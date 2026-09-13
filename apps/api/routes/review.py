"""
Reviewer sign-off, interactive questions, and async job polling routes.

Endpoints:
- GET  /jobs/{id} (rate-limited via MAX_STATUS_POLLS_PER_MIN)
- POST /jobs/{id}/cancel (releases active-job spend guard reservation)
- POST /applications/{id}/questions
- POST /applications/{id}/review
"""

from typing import Optional, List, Dict, Any, Literal
import asyncio
import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from apps.api.config import settings

from apps.api.db.models import ApplicationModel, JobModel, AuditEventModel, utc_now
from apps.api.db.session import get_db
from apps.api.middleware.rate_limit import get_redis_client, rate_limit_polling
from apps.api.middleware.spend_guard import release_active_job_by_id

logger = logging.getLogger("finscan.review")

router = APIRouter(tags=["Review & Jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    application_id: str
    status: str
    attempt_count: int
    error_message: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED", "NEEDS_INFO"]
    reviewer_id: str
    notes: Optional[str] = None
    corrections: List[Dict[str, Any]] = []
    confirm_app_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = None


class QuestionResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]


def _enforce_review_invariants(decision: str, notes: Optional[str], corrections: List[Dict[str, Any]], confirm_app_id: Optional[str], app_id: str) -> str:
    """Server-side dual-sign friction gate (AGENTS §5.3). Returns sanitized notes."""
    clean_notes = (notes or "").strip()
    if decision in ("REJECTED", "NEEDS_INFO") and len(clean_notes) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Substantive audit rationale (>=5 characters) is required for REJECTED/NEEDS_INFO",
        )
    if len(clean_notes) > 5000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Notes exceed 5000 characters")
    if len(corrections) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many corrections (max 50)")
    if confirm_app_id is not None and confirm_app_id.strip() != app_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dossier identifier challenge failed: typed ID must exactly match application ID",
        )
    return clean_notes


@router.get(
    "/jobs/{id}",
    response_model=JobStatusResponse,
    dependencies=[Depends(rate_limit_polling)],
)
async def get_job_status(
    id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Poll authoritative processing job status from PostgreSQL JobModel.
    Enforces MAX_STATUS_POLLS_PER_MIN rate limit via Redis.
    Returns 404 for unknown jobs.
    """
    result = await session.execute(
        select(JobModel).where(JobModel.id == id)
    )
    job_record = result.scalar_one_or_none()
    if not job_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{id}' not found",
        )

    return JobStatusResponse(
        job_id=job_record.id,
        application_id=job_record.application_id,
        status=job_record.status,
        attempt_count=job_record.attempt_count,
        error_message=job_record.error_message,
    )


@router.post("/jobs/{id}/cancel")
async def cancel_job(
    id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """
    Cancel a queued or running processing job and atomically release
    its spend guard reservation slot in Redis.
    - Loads and locks both job and application in one transaction.
    - Rejects terminal jobs with 409 Conflict.
    - Transitions both to CANCELLED.
    - Appends status transition to state_json.
    - Records immutable audit event.
    - Releases Redis reservation only after DB commit succeeds.
    """
    # 1. Lock and load job
    stmt = select(JobModel).where(JobModel.id == id)
    try:
        bind = session.get_bind()
        if bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()
    except Exception:
        pass

    result = await session.execute(stmt)
    job_record = result.scalar_one_or_none()
    if not job_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{id}' not found",
        )

    # 2. Enforce only cancellable from QUEUED or PROCESSING
    if job_record.status not in ("QUEUED", "PROCESSING"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job '{id}' in status '{job_record.status}' cannot be cancelled. Only QUEUED or PROCESSING jobs can be cancelled.",
        )

    # 3. Lock and load parent application
    app_stmt = select(ApplicationModel).where(ApplicationModel.id == job_record.application_id)
    try:
        bind = session.get_bind()
        if bind.dialect.name == "postgresql":
            app_stmt = app_stmt.with_for_update()
    except Exception:
        pass

    app_result = await session.execute(app_stmt)
    app_model = app_result.scalar_one_or_none()
    if not app_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{job_record.application_id}' for job '{id}' not found",
        )

    now = utc_now()
    from_app_status = app_model.status

    # 4. Mutate relational status
    job_record.status = "CANCELLED"
    job_record.updated_at = now

    app_model.status = "CANCELLED"
    app_model.updated_at = now

    # 5. Mutate state_json and append status transition
    state = dict(app_model.state_json or {})
    state["status"] = "CANCELLED"
    history = list(state.get("status_history", []))
    history.append({
        "from_status": from_app_status,
        "to_status": "CANCELLED",
        "timestamp": now.isoformat(),
        "reason": f"Job {id} cancelled by user request",
    })
    state["status_history"] = history
    app_model.state_json = state

    # 6. Insert immutable audit event
    actor = request.headers.get("x-user-id") or "user"
    audit_event = AuditEventModel(
        id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
        application_id=app_model.id,
        from_status=from_app_status,
        to_status="CANCELLED",
        actor=actor,
        decision="CANCELLED",
        notes=f"Job {id} cancelled",
        corrections=None,
        timestamp=now,
    )
    session.add(audit_event)

    # 7. Commit database transaction atomically
    await session.commit()

    # 8. Release Redis active-job reservation ONLY after DB commit succeeds
    if redis_client is not None:
        try:
            await release_active_job_by_id(redis_client, id)
        except Exception as redis_err:
            logger.warning(f"Failed to release Redis reservation for cancelled job {id}: {redis_err}")

    return {"job_id": id, "status": "CANCELLED"}


def _build_findings_context(state_json: Dict[str, Any]) -> "tuple[str, List[str]]":
    """
    Formats this application's OWN deterministic findings (core/rules/) as a
    trusted context block the Q&A LLM can explain from - this is what actually
    lets it answer "why was this application flagged/rejected", not just
    generic policy lookup. These are NOT LLM-generated (Prime Invariant:
    deterministic code decides, the LLM only narrates), so including their
    exact text verbatim is safe; the grounding firewall additionally requires
    the model to bracket-cite [RULE_ID] when explaining one, using the same
    citation mechanism as policy chunks (see authorized_chunk_ids below) - one
    consistent grounding check, not a special-cased exception for findings.

    Returns (context_text, rule_ids_present). context_text is "" when the
    application has no findings yet (e.g. still processing).
    """
    findings = state_json.get("findings") or []
    rule_ids: List[str] = []
    lines: List[str] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        rule_id = str(f.get("rule_id", "UNKNOWN"))
        rule_ids.append(rule_id)
        lines.append(
            f"- [{rule_id}] {f.get('rule_name', '')} (verdict={f.get('verdict', 'unknown')}): {f.get('reason', '')}"
        )
    if not lines:
        return "", []
    context = "Deterministic Application Findings (already verified - cite as [RULE_ID]):\n" + "\n".join(lines)
    return context, rule_ids


def _finding_evidence_citations(state_json: Dict[str, Any], cited_rule_ids: set) -> List[Dict[str, Any]]:
    """
    Turns each ACTUALLY-cited finding's supporting_evidence into jump-to-evidence
    citations, the same shape the policy-hit citations above use - this is what
    lets the underwriter click "why was this flagged" straight to the exact
    page/box on the PDF canvas that produced the finding, not just read the
    reason as prose. Scoped to rule_ids the model actually cited in its answer
    (not every finding on the application) so unrelated flags don't clutter an
    answer about something else.
    """
    out: List[Dict[str, Any]] = []
    for f in state_json.get("findings") or []:
        if not isinstance(f, dict) or f.get("rule_id") not in cited_rule_ids:
            continue
        for ev in f.get("supporting_evidence") or []:
            if not isinstance(ev, dict):
                continue
            text = str(ev.get("quoted_span", "")).strip()
            out.append(
                {
                    "chunk_id": f"FINDING-{f.get('rule_id')}",
                    "policy_id": None,
                    "section": f.get("rule_name"),
                    "page_number": ev.get("page_number"),
                    "score": None,
                    "text": text,
                    "excerpt": text[:400],
                    "is_policy": False,
                    "document_id": ev.get("document_id"),
                    "document_type": ev.get("document_type") or "document",
                    "bounding_box": ev.get("bounding_box"),
                }
            )
    return out


@router.post("/applications/{id}/questions", response_model=QuestionResponse)
async def ask_question(id: str, payload: QuestionRequest, session: AsyncSession = Depends(get_db)):
    """
    RAG-grounded question answering over the credit policy corpus AND this
    application's own deterministic findings - the latter is what lets an
    underwriter ask "why was this flagged/rejected?" and get an explanation
    grounded in the actual computed reasons, not a generic policy summary.

    Every answer that reaches the underwriter (agentic or single-shot) is
    firewalled through core/rag/grounding.py: it must cite at least one real
    policy chunk or finding rule_id, or it is withheld rather than returned
    as if it were evidence-backed (Prime Invariant: no hallucinated content).
    """
    from sqlalchemy import select as _select

    from apps.api.db.models import ApplicationModel as _ApplicationModel

    result = await session.execute(
        _select(_ApplicationModel).where(_ApplicationModel.id == id)
    )
    app_model = result.scalar_one_or_none()
    if app_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )
    findings_context, finding_rule_ids = _build_findings_context(dict(app_model.state_json or {}))

    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty",
        )
    if len(question) > 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question exceeds 1000 characters")
    # Prompt-injection hygiene: delimit inquiry, strip control chars; retriever+grounding treat it as data.
    question = " ".join(question.split())
    raw_history = [m.model_dump() for m in payload.history] if payload.history else None

    try:
        from core.rag.indexer import IndexManager
        from core.rag.retriever import HybridRetriever

        policy_dir = _resolve_policy_dir()
        manager = IndexManager()
        manager.load_policy_corpus(policy_dir=policy_dir)

        # Index applicant's own documents for dossier retrieval
        app_state = dict(app_model.state_json or {})
        doc_texts = app_state.get("document_texts") or {}
        classified_types = app_state.get("classified_types") or {}
        if doc_texts:
            try:
                manager.index_application_dossier(id, doc_texts, classified_types=classified_types)
            except Exception as idx_err:
                logger.warning(f"Failed to index dossier in review route for '{id}': {idx_err}")

        retriever = HybridRetriever(index_manager=manager, policy_dir=policy_dir)

        # Retrieve relevant passages from policy
        policy_hits = retriever.retrieve_policy(question, top_k=3)

        # Retrieve relevant passages from applicant dossier
        dossier_hits = []
        try:
            dossier_hits = retriever.retrieve_dossier(id, question, top_k=3)
        except Exception as d_err:
            logger.debug(f"Dossier retrieval not available for '{id}': {d_err}")

        hits = dossier_hits + policy_hits
    except Exception as err:
        logger.warning(f"Retrieval unavailable for question on '{id}': {err}")
        hits = []

    # Only abstain immediately when there is truly nothing to answer from:
    # no policy passages, no dossier passages, AND no application findings to explain.
    if not hits and not findings_context and not settings.AGENTIC_QA_ENABLED:
        return QuestionResponse(
            answer="No relevant policy passages or dossier evidence found for this question. I abstain rather than guess.",
            citations=[],
        )

    # Experimental: read-only tool-calling agent (apps/api/agent.py), off by default.
    if settings.AGENTIC_QA_ENABLED:
        from apps.api.agent import answer_question_agentic

        agentic_result = answer_question_agentic(
            question,
            retriever,
            application_id=id,
            findings_context=findings_context,
            extra_authorized_ids=finding_rule_ids,
            chat_history=raw_history,
        )
        if agentic_result is not None:
            cited_rules = {rid for rid in finding_rule_ids if f"[{rid}]" in agentic_result["answer"]}
            return QuestionResponse(
                answer=agentic_result["answer"],
                citations=agentic_result["citations"]
                + _finding_evidence_citations(dict(app_model.state_json or {}), cited_rules),
            )

    citations: List[Dict[str, Any]] = []
    for hit in hits:
        text = str(hit.get("text", "")).strip()
        excerpt = text[:400] + ("..." if len(text) > 400 else "")
        doc_id = hit.get("doc_id") or hit.get("document_id")
        is_policy = bool(hit.get("is_policy", True))
        page_number = hit.get("page_number")
        citation: Dict[str, Any] = {
            "chunk_id": hit.get("chunk_id"),
            "policy_id": doc_id if is_policy else None,
            "section": f"Page {page_number}" if page_number else None,
            "page_number": page_number,
            "score": hit.get("score"),
            "text": text,
            "excerpt": excerpt,
            "is_policy": is_policy,
        }
        # `document_id` is the Citation contract's jump-to-evidence key. Only a
        # chunk from an uploaded dossier document can be located on the PDF
        # canvas; policy-corpus chunks stay read-only rather than sending the
        # viewer after a document id that is not in this application.
        if not is_policy and doc_id:
            citation["document_id"] = doc_id
            citation["document_type"] = hit.get("document_type") or "document"
            citation["bounding_box"] = hit.get("bounding_box")
        citations.append(citation)

    # If LLM is configured (e.g. Groq, OpenCode, or OpenAI), generate grounded synthesis
    answer_text = None
    if os.getenv("GROQ_API_KEY") or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY"):
        try:
            from adapters.llm.opencode import OpenCodeZenLLM
            from core.rag.grounding import sanitize_summary_text

            llm = OpenCodeZenLLM()
            raw_answer = llm.answer_question(
                question,
                hits,
                findings_context=findings_context,
                chat_history=raw_history,
            )
            authorized_ids = [h.get("chunk_id") for h in hits if h.get("chunk_id")] + list(finding_rule_ids)
            answer_text = sanitize_summary_text(raw_answer, authorized_chunk_ids=authorized_ids)
        except Exception as llm_err:
            logger.warning(f"LLM answer_question failed, falling back to passage citations: {llm_err}")

    if not answer_text:
        lines: List[str] = []
        if findings_context:
            lines.append(findings_context)
        if hits:
            policy_count = len([h for h in hits if h.get("is_policy")])
            dossier_count = len([h for h in hits if not h.get("is_policy")])
            lines.append(f"Top passages relevant to: {question} ({dossier_count} from dossier, {policy_count} from policy)")
            for i, hit in enumerate(hits, start=1):
                text = str(hit.get("text", "")).strip()
                excerpt = text[:400] + ("..." if len(text) > 400 else "")
                src = "Policy" if hit.get("is_policy", True) else f"Document {hit.get('doc_id')}"
                lines.append(f"{i}. [{hit.get('chunk_id')}] ({src}) {excerpt}")
        if not lines:
            lines = ["No relevant policy passages, dossier evidence, or application findings available for this question. I abstain rather than guess."]
        answer_text = "\n".join(lines)

    cited_rules = {rid for rid in finding_rule_ids if f"[{rid}]" in answer_text}
    if cited_rules:
        citations = citations + _finding_evidence_citations(dict(app_model.state_json or {}), cited_rules)

    return QuestionResponse(answer=answer_text, citations=citations)


def _resolve_policy_dir() -> str:
    """Locates the policy corpus: env override, else repo policies/, else ./policies."""
    env_dir = os.getenv("FINSCAN_POLICY_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    repo_policies = os.path.join(repo_root, "policies")
    if os.path.isdir(repo_policies):
        return repo_policies
    return "policies"


@router.post("/applications/{id}/review")
async def submit_review(
    id: str,
    payload: ReviewDecisionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """
    Submit human underwriter sign-off or request for information.
    - Requires auth (mock passthrough local; verified user in google/required).
    - Server-enforces dual-sign friction: notes>=5 for REJECTED/NEEDS_INFO + dossier-ID challenge.
    - Actor is the verified user email, NOT the spoofable body reviewer_id.
    """
    from apps.api.auth.deps import get_current_user as _get_user

    try:
        actor_user = await _get_user(request, session)
        actor_email = actor_user.email
    except HTTPException:
        # Mock mode never raises; google/required enforces 401/403 here.
        raise
    clean_notes = _enforce_review_invariants(
        payload.decision, payload.notes, payload.corrections, payload.confirm_app_id, id
    )
    stmt = select(ApplicationModel).where(ApplicationModel.id == id)
    try:
        bind = session.get_bind()
        if bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update()
    except Exception:
        pass

    result = await session.execute(stmt)
    app_model = result.scalar_one_or_none()

    if not app_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )

    if app_model.status != "READY_FOR_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application '{id}' in status '{app_model.status}' cannot be reviewed. Must be READY_FOR_REVIEW.",
        )

    if payload.decision in ("APPROVED", "REJECTED"):
        to_status = "REVIEWED"
    elif payload.decision == "NEEDS_INFO":
        to_status = "NEEDS_INFORMATION"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review decision: {payload.decision}",
        )

    now = utc_now()
    from_status = app_model.status

    # 1. Update relational fields (actor = verified email; body reviewer_id ignored except mock display)
    app_model.status = to_status
    app_model.reviewer_id = actor_email
    app_model.updated_at = now

    # 2. Update state_json
    state = dict(app_model.state_json or {})
    state["status"] = to_status
    state["reviewer_id"] = actor_email
    state["reviewer_decision"] = payload.decision
    state["reviewer_notes"] = clean_notes
    state["corrections_applied"] = payload.corrections
    state["review_paused"] = False

    history = list(state.get("status_history", []))
    history.append({
        "from_status": from_status,
        "to_status": to_status,
        "timestamp": now.isoformat(),
        "reason": f"Human review decision: {payload.decision} by {actor_email}",
    })
    state["status_history"] = history
    app_model.state_json = state

    # 3. Record immutable audit event
    audit_event = AuditEventModel(
        id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
        application_id=id,
        from_status=from_status,
        to_status=to_status,
        actor=actor_email,
        decision=payload.decision,
        notes=clean_notes,
        corrections={"corrections": payload.corrections} if isinstance(payload.corrections, list) else payload.corrections,
        timestamp=now,
    )
    session.add(audit_event)

    # 4. Atomic commit
    await session.commit()

    # 5. Best-effort LangGraph checkpoint resume: advances the paused
    # StateGraph thread through human_review_node so the durable checkpoint
    # mirrors the DB decision. Never fails the API response — the DB commit
    # above is the source of truth for the UI.
    try:
        from core.graph.checkpoint import SqliteSaver
        from core.graph.workflow import resume_application_review

        checkpoint_path = os.getenv("CHECKPOINT_DB_PATH", "data/storage/checkpoints.sqlite3")

        def _resume() -> None:
            resume_application_review(
                thread_id=id,
                decision=payload.decision,  # type: ignore[arg-type]
                notes=payload.notes,
                corrections=payload.corrections,
                checkpointer=SqliteSaver(db_path=checkpoint_path),
            )

        await asyncio.to_thread(_resume)
    except Exception as resume_err:  # noqa: BLE001 - resume is advisory only
        logger.warning(f"Graph resume skipped for application '{id}': {resume_err}")

    return {
        "application_id": id,
        "decision": payload.decision,
        "status": to_status,
        "reviewer_id": actor_email,
        "notes": clean_notes,
        "from_status": from_status,
        "to_status": to_status,
    }

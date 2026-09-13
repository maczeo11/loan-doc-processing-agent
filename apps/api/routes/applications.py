"""
Application dossier persistence and processing enqueue routes for FinScan AI.

Core Requirements:
- POST /applications: Creates initial ApplicationModel with minimal LoanApplicationState.
- GET /applications/{id}: Fetches authoritative application state.
- POST /applications/{id}/process: Atomic transaction validating document presence,
  enforcing active-job spend guards, transitioning status to QUEUED, creating JobModel,
  and enqueuing JobRef outbox event.
- Enforces strict state transitions and idempotency for QUEUED/PROCESSING jobs.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from apps.api.config import settings
from apps.api.db.models import ApplicationModel, DocumentModel, JobModel, utc_now
from apps.api.db.session import get_db
from apps.api.middleware.rate_limit import get_redis_client, resolve_user_identity
from apps.api.middleware.spend_guard import reserve_active_job_slot, release_active_job_slot
from core.contracts.jobs import JobRef
from apps.api.db.outbox import create_outbox_event

logger = logging.getLogger("finscan.applications")

router = APIRouter(prefix="/applications", tags=["Applications"])


class CreateApplicationRequest(BaseModel):
    applicant_name: str
    loan_amount: float
    loan_purpose: Optional[str] = None


class CreateApplicationResponse(BaseModel):
    application_id: str
    status: str


class ProcessApplicationResponse(BaseModel):
    job_id: str
    application_id: str
    status: str


def build_minimal_application_state(application_id: str) -> Dict[str, Any]:
    """
    Initializes a valid minimal LoanApplicationState matching core/contracts/state.py.
    """
    now_iso = utc_now().isoformat()
    return {
        "application_id": application_id,
        "status": "UPLOADED",
        "status_history": [
            {
                "from_status": "UPLOADED",
                "to_status": "UPLOADED",
                "timestamp": now_iso,
                "reason": "Application dossier created",
            }
        ],
        "document_ids": [],
        "document_manifest": {},
        "classified_types": {},
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": False,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateApplicationResponse)
async def create_application(
    payload: CreateApplicationRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new loan application container.
    Persists application in PostgreSQL with initial UPLOADED status and minimal state JSON.
    """
    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    initial_state = build_minimal_application_state(app_id)

    app_model = ApplicationModel(
        id=app_id,
        applicant_name=payload.applicant_name,
        loan_amount=payload.loan_amount,
        loan_purpose=payload.loan_purpose,
        status="UPLOADED",
        reviewer_id=None,
        state_json=initial_state,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(app_model)
    await session.commit()

    return CreateApplicationResponse(
        application_id=app_id,
        status="UPLOADED",
    )


@router.get("", response_model=list[dict[str, Any]])
async def list_applications(
    session: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    """
    List most recent loan applications for selection in underwriter UI.
    """
    stmt = select(ApplicationModel).order_by(ApplicationModel.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "application_id": app.id,
            "applicant_name": app.applicant_name or "Applicant",
            "loan_amount": app.loan_amount,
            "loan_purpose": app.loan_purpose,
            "status": app.status,
            # REVIEWED covers both APPROVED and REJECTED outcomes; the dashboard
            # list needs this to avoid rendering an identical "signed off" pill
            # for a rejected dossier.
            "reviewer_decision": (app.state_json or {}).get("reviewer_decision"),
            "created_at": app.created_at.isoformat() if app.created_at else None,
        }
        for app in rows
    ]


@router.get("/{id}")
async def get_application(
    id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve authoritative application state, facts, findings, and review status.
    Returns 404 for unknown applications.
    """
    result = await session.execute(
        select(ApplicationModel).where(ApplicationModel.id == id)
    )
    app_model = result.scalar_one_or_none()

    if not app_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )

    state = dict(app_model.state_json or {})
    state["application_id"] = app_model.id
    state["status"] = app_model.status
    # Relational columns the pipeline never writes into state_json, but which
    # the reviewer UI needs (loan amount, applicant of record, clock start).
    state["loan_amount"] = app_model.loan_amount
    state["loan_purpose"] = app_model.loan_purpose
    state["applicant_name"] = app_model.applicant_name
    state["created_at"] = app_model.created_at.isoformat() if app_model.created_at else None
    state["updated_at"] = app_model.updated_at.isoformat() if app_model.updated_at else None
    state["reviewer_id"] = app_model.reviewer_id
    return state


@router.post("/{id}/process", status_code=status.HTTP_202_ACCEPTED, response_model=ProcessApplicationResponse)
async def trigger_processing(
    id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """
    Queue application for processing.
    Atomically verifies document presence, reserves active-job spend guard slot,
    updates application status to QUEUED, appends status transition,
    persists JobModel, and inserts OutboxEventModel in a single transaction.
    Returns 202 Accepted with job ID.
    """
    # 1. Fetch application with row-level locking on PostgreSQL
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

    # 2. Idempotency handling: If already QUEUED or PROCESSING, return existing active job
    # Crucial rule: Do NOT consume extra spend-guard reservation slots on idempotent queries
    if app_model.status in ("QUEUED", "PROCESSING"):
        job_stmt = (
            select(JobModel)
            .where(
                JobModel.application_id == id,
                JobModel.status.in_(["QUEUED", "PROCESSING"]),
            )
            .order_by(JobModel.created_at.desc())
            .limit(1)
        )
        job_res = await session.execute(job_stmt)
        existing_job = job_res.scalar_one_or_none()
        if existing_job:
            return ProcessApplicationResponse(
                job_id=existing_job.id,
                application_id=id,
                status=app_model.status,
            )

    # 3. Transition check: Prevent queueing only if already sealed (REVIEWED) or currently active
    # Underwriters can freely re-run after uploading documents, reclassifying, or investigating
    # in READY_FOR_REVIEW, NEEDS_INFORMATION, FAILED, and CANCELLED.
    ALLOWED_PROCESS_STATUSES = {"UPLOADED", "READY_FOR_REVIEW", "NEEDS_INFORMATION", "FAILED", "CANCELLED"}
    if app_model.status not in ALLOWED_PROCESS_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application '{id}' in status '{app_model.status}' cannot be transitioned to QUEUED",
        )

    # 4. Document presence validation: Reliably query persisted DocumentModel rows
    doc_stmt = (
        select(DocumentModel)
        .where(DocumentModel.application_id == id)
        .order_by(DocumentModel.created_at.asc())
    )
    doc_rows = (await session.execute(doc_stmt)).scalars().all()
    if not doc_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application '{id}' has no uploaded documents. At least one document is required for processing.",
        )

    doc_ids = [doc.id for doc in doc_rows]
    doc_manifest = {doc.id: doc.storage_uri for doc in doc_rows}

    # 5. Spend guard: Reserve active-job slot before mutating state
    user_id = resolve_user_identity(request)
    job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

    async def resolve_finished_job_ids(candidate_ids) -> set[str]:
        """
        Which reserved jobs have already finished, per the authoritative JobModel.

        Nothing released a slot on successful completion, so a finished job kept
        occupying one until the reservation TTL lapsed.
        """
        candidates = [str(c) for c in candidate_ids]
        if not candidates:
            return set()
        rows = (
            await session.execute(
                select(JobModel.id, JobModel.status).where(JobModel.id.in_(candidates))
            )
        ).all()
        known = {row.id: row.status for row in rows}
        finished = {
            jid
            for jid in candidates
            # An id Redis holds but the DB has never seen is stale too.
            if known.get(jid, "MISSING") not in ("QUEUED", "PROCESSING")
        }
        return finished

    slot_reserved = await reserve_active_job_slot(
        redis_client=redis_client,
        user_id=user_id,
        job_id=job_id,
        max_active=settings.MAX_ACTIVE_JOBS_PER_USER,
        ttl_seconds=settings.SPEND_GUARD_RESERVATION_TTL_SECONDS,
        resolve_finished_job_ids=resolve_finished_job_ids,
    )
    if not slot_reserved:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Active job limit exceeded ({settings.MAX_ACTIVE_JOBS_PER_USER} concurrent jobs allowed). "
                "Wait for an in-flight dossier to finish, or cancel one from its inspector panel."
            ),
        )

    now = utc_now()
    from_status = app_model.status
    app_model.status = "QUEUED"
    app_model.updated_at = now

    # Update state_json with status and transition
    state = dict(app_model.state_json or {})
    state["status"] = "QUEUED"
    history = list(state.get("status_history", []))
    history.append({
        "from_status": from_status,
        "to_status": "QUEUED",
        "timestamp": now.isoformat(),
        "reason": "Processing triggered via API",
    })
    state["status_history"] = history
    app_model.state_json = state

    # 6. Create JobModel
    job_record = JobModel(
        id=job_id,
        application_id=id,
        status="QUEUED",
        attempt_count=1,
        created_at=now,
        updated_at=now,
    )
    session.add(job_record)

    # 7. Create Transactional Outbox Event with exact JobRef contract
    job_ref = JobRef(
        job_id=job_id,
        application_id=id,
        attempt_count=1,
        created_at=now.isoformat(),
        priority=0,
        metadata={
            "document_ids": doc_ids,
            "document_manifest": doc_manifest,
        },
    )
    create_outbox_event(
        session=session,
        aggregate_type="application_job",
        aggregate_id=id,
        payload=job_ref,
    )

    # 8. Commit single atomic transaction; release spend guard slot if DB fails
    try:
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        # Cleanly release spend-guard reservation on DB failure
        await release_active_job_slot(redis_client=redis_client, user_id=user_id, job_id=job_id)
        logger.error(f"Failed to commit processing job transaction for application '{id}': {db_err}", exc_info=True)
        raise

    return ProcessApplicationResponse(
        job_id=job_id,
        application_id=id,
        status="QUEUED",
    )


@router.get("/{id}/audit")
async def list_audit_events(
    id: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Read the append-only audit trail for a dossier.

    Every sign-off and cancellation writes an AuditEventModel row; without this
    route the "immutable audit trail" promised at sign-off was invisible to the
    underwriter who is accountable for it.
    """
    from apps.api.db.models import AuditEventModel

    result = await session.execute(
        select(ApplicationModel).where(ApplicationModel.id == id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )

    stmt = (
        select(AuditEventModel)
        .where(AuditEventModel.application_id == id)
        .order_by(AuditEventModel.timestamp.asc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": event.id,
            "application_id": event.application_id,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "actor": event.actor,
            "decision": event.decision,
            "notes": event.notes,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }
        for event in rows
    ]


# Exporting a Credit Appraisal Memo before a human has signed it off would put a
# bank-letterhead PDF behind an unreviewed machine verdict.
EXPORTABLE_STATUSES = ("READY_FOR_REVIEW", "REVIEWED", "NEEDS_INFORMATION")


@router.get("/{id}/export")
async def export_application(
    id: str,
    format: str = "json",
    session: AsyncSession = Depends(get_db),
):
    """
    Export finalized dossier analysis.
    - format=json: full application state (facts, findings, memo, citations).
    - format=pdf: generated Credit Appraisal Memo PDF (reportlab).
    Returns 404 for unknown applications, 409 before the pipeline has produced a
    reviewable dossier, 400 for unsupported formats.
    """
    result = await session.execute(
        select(ApplicationModel).where(ApplicationModel.id == id)
    )
    app_model = result.scalar_one_or_none()
    if not app_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found",
        )

    if app_model.status not in EXPORTABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Application '{id}' in status '{app_model.status}' has no appraisal to export. "
                f"Run the verification pipeline first (exportable: {', '.join(EXPORTABLE_STATUSES)})."
            ),
        )

    state = dict(app_model.state_json or {})
    state["application_id"] = app_model.id
    state["status"] = app_model.status

    if format == "json":
        return {"application_id": id, "export_format": "json", "analysis": state}

    if format == "pdf":
        import os
        import tempfile

        from fastapi.responses import Response as _Response

        from core.reporting.exporter import export_reviewed_dossier_pdf

        # applicant_name lives on the relational model, not state_json.
        state["applicant_name"] = app_model.applicant_name

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_path = tmp.name
        tmp.close()
        try:
            export_reviewed_dossier_pdf(state, tmp_path)
            # Read-then-delete: FileResponse would stream a file nothing ever
            # unlinks, leaking one temp PDF per download.
            with open(tmp_path, "rb") as handle:
                pdf_bytes = handle.read()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(exc),
            ) from exc
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                logger.warning(f"Could not remove temporary export file '{tmp_path}'")

        return _Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{id}_credit_appraisal.pdf"',
            },
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported export format '{format}'. Use 'json' or 'pdf'.",
    )

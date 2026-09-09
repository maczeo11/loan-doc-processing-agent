"""
Reviewer sign-off, interactive questions, and async job polling routes.

Endpoints:
- GET  /jobs/{id} (rate-limited via MAX_STATUS_POLLS_PER_MIN)
- POST /jobs/{id}/cancel (releases active-job spend guard reservation)
- POST /applications/{id}/questions
- POST /applications/{id}/review
"""

from typing import Optional, List, Dict, Any, Literal
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

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


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]


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


@router.post("/applications/{id}/questions", response_model=QuestionResponse)
async def ask_question(id: str, payload: QuestionRequest):
    """
    RAG-grounded question answering over the application documents and credit policy.
    """
    # Sai Mokshith to implement hybrid retrieval + grounding validation
    return QuestionResponse(
        answer="Grounding answer placeholder.",
        citations=[]
    )


@router.post("/applications/{id}/review")
async def submit_review(
    id: str,
    payload: ReviewDecisionRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Submit human underwriter sign-off or request for information.
    - Loads and locks application container.
    - Enforces transition strictly from READY_FOR_REVIEW.
    - Maps decision: APPROVED -> REVIEWED, REJECTED -> REVIEWED, NEEDS_INFO -> NEEDS_INFORMATION.
    - Atomically updates relational model and state_json (status, reviewer_decision, reviewer_notes,
      corrections_applied, status_history, review_paused, reviewer_id).
    - Persists an immutable AuditEventModel record.
    """
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

    # 1. Update relational fields
    app_model.status = to_status
    app_model.reviewer_id = payload.reviewer_id
    app_model.updated_at = now

    # 2. Update state_json
    state = dict(app_model.state_json or {})
    state["status"] = to_status
    state["reviewer_id"] = payload.reviewer_id
    state["reviewer_decision"] = payload.decision
    state["reviewer_notes"] = payload.notes
    state["corrections_applied"] = payload.corrections
    state["review_paused"] = False

    history = list(state.get("status_history", []))
    history.append({
        "from_status": from_status,
        "to_status": to_status,
        "timestamp": now.isoformat(),
        "reason": f"Human review decision: {payload.decision} by {payload.reviewer_id}",
    })
    state["status_history"] = history
    app_model.state_json = state

    # 3. Record immutable audit event
    audit_event = AuditEventModel(
        id=f"AUDIT-{uuid.uuid4().hex[:8].upper()}",
        application_id=id,
        from_status=from_status,
        to_status=to_status,
        actor=payload.reviewer_id,
        decision=payload.decision,
        notes=payload.notes,
        corrections={"corrections": payload.corrections} if isinstance(payload.corrections, list) else payload.corrections,
        timestamp=now,
    )
    session.add(audit_event)

    # 4. Atomic commit
    await session.commit()

    return {
        "application_id": id,
        "decision": payload.decision,
        "status": to_status,
    }

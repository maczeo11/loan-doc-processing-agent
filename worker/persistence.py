"""
Worker Postgres write-back (Bhanu Teja zone).

Closes the loop between the LangGraph pipeline and the authoritative API state:
after the StateGraph finishes, the worker persists the final state to
PostgreSQL (JobModel + ApplicationModel.state_json) in a single transaction
BEFORE the queue message is acknowledged (acknowledge-last guarantee).

Deliberately dependency-light: sync SQLAlchemy + psycopg only.
No FastAPI/Redis/provider imports here, and nothing in core/ is touched.
Persistence is opt-in — ApplicationWorker only calls this when constructed
with an explicit db_url, so unit tests using fake queues stay hermetic.
"""

import logging
from typing import Any, Dict, List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import ApplicationModel, JobModel, utc_now

logger = logging.getLogger("finscan.worker.persistence")

# Fields copied from the LangGraph final state into ApplicationModel.state_json.
COPIED_STATE_FIELDS = (
    "status",
    "findings",
    "missing_documents",
    "classified_types",
    "document_pages",
    "ocr_routes",
    "applicant",
    "payslip",
    "bank_statement",
    "tax_return",
    "retrieved_chunk_ids",
    "summary_markdown",
    "summary_grounded",
    "review_paused",
)


def to_jsonable(value: Any) -> Any:
    """Recursively converts Pydantic models (Finding/Facts) to plain JSON data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return str(value)


def normalize_sync_dsn(dsn: str) -> str:
    """Worker env may carry an asyncpg DSN; sync engine needs psycopg."""
    if dsn.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + dsn[len("postgresql+asyncpg://"):]
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn[len("postgresql://"):]
    return dsn


def persist_pipeline_result(
    db_url: str,
    job_id: str,
    application_id: str,
    final_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Persists one LangGraph pipeline outcome to PostgreSQL atomically.

    - JobModel -> SUCCEEDED (READY_FOR_REVIEW) or FAILED, error cleared/set.
    - ApplicationModel -> status + merged state_json (history appended,
      findings/memo/facts replaced with worker-computed values).

    Raises on any failure so the caller can fail() the delivery retryably
    WITHOUT acknowledging it (acknowledge-last).
    """
    engine = create_engine(normalize_sync_dsn(db_url), pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app_status = str(final_state.get("status", "FAILED"))
    now = utc_now()
    try:
        with factory() as session:
            job = session.execute(
                select(JobModel).where(JobModel.id == job_id).with_for_update()
            ).scalar_one_or_none()
            if job is None:
                raise RuntimeError(f"Job '{job_id}' not found; refusing to ack blind")

            app = session.execute(
                select(ApplicationModel)
                .where(ApplicationModel.id == application_id)
                .with_for_update()
            ).scalar_one_or_none()
            if app is None:
                raise RuntimeError(f"Application '{application_id}' not found; refusing to ack blind")

            if app_status == "READY_FOR_REVIEW":
                job.status = "SUCCEEDED"
                job.error_message = None
            else:
                job.status = "FAILED"
                job.error_message = f"Pipeline ended in unexpected status '{app_status}'"
            job.updated_at = now

            merged: Dict[str, Any] = dict(app.state_json or {})
            existing_history: List[Any] = list(merged.get("status_history", []))
            worker_history: List[Any] = list(final_state.get("status_history", []))
            merged["status_history"] = existing_history + [
                h for h in worker_history if h not in existing_history
            ]
            for field in COPIED_STATE_FIELDS:
                if field in final_state:
                    merged[field] = to_jsonable(final_state[field])
            merged["status"] = app_status
            merged["application_id"] = app.id

            app.status = app_status
            app.state_json = merged
            app.updated_at = now

            session.commit()
            logger.info(
                f"Write-back committed for job {job_id} "
                f"(app={application_id} status={app_status} "
                f"findings={len(merged.get('findings', []))})"
            )
            return {"job_status": job.status, "app_status": app_status}
    finally:
        engine.dispose()


def persist_job_failure(
    db_url: str,
    job_id: str,
    application_id: str,
    error_message: str,
    terminal: bool,
) -> None:
    """
    Record a pipeline failure so the dossier leaves QUEUED/PROCESSING.

    Without this, an exception or a DLQ-routed poison message left the
    application pinned at QUEUED forever while the UI polled a spinner with no
    error and no way out.

    - `terminal=True` (DLQ / attempt ceiling): application -> FAILED, job -> FAILED.
    - `terminal=False` (retryable): job records the error and attempt count, but
      the application stays QUEUED because a redelivery is still expected.

    Best-effort by contract: raising here would mask the original failure, so
    callers log and continue.
    """
    engine = create_engine(normalize_sync_dsn(db_url), pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    now = utc_now()
    try:
        with factory() as session:
            job = session.execute(
                select(JobModel).where(JobModel.id == job_id).with_for_update()
            ).scalar_one_or_none()
            if job is not None:
                job.status = "FAILED" if terminal else "QUEUED"
                job.error_message = error_message[:1000]
                job.updated_at = now

            if not terminal:
                session.commit()
                return

            app = session.execute(
                select(ApplicationModel)
                .where(ApplicationModel.id == application_id)
                .with_for_update()
            ).scalar_one_or_none()
            if app is not None:
                from_status = app.status
                merged: Dict[str, Any] = dict(app.state_json or {})
                history: List[Any] = list(merged.get("status_history", []))
                history.append(
                    {
                        "from_status": from_status,
                        "to_status": "FAILED",
                        "timestamp": now.isoformat(),
                        "reason": f"Pipeline failed: {error_message[:200]}",
                    }
                )
                merged["status_history"] = history
                merged["status"] = "FAILED"
                merged["application_id"] = app.id
                app.status = "FAILED"
                app.state_json = merged
                app.updated_at = now

            session.commit()
            logger.info(f"Recorded terminal failure for job {job_id} (app={application_id})")
    finally:
        engine.dispose()

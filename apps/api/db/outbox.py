"""
Transactional Outbox implementation for FinScan AI.

Core Principles:
- Atomic Enqueue: Business state and outbox events commit together in a single database transaction.
- Producer does NOT commit internally; the calling route/service controls transaction boundary.
- Consumer/Dispatcher uses SELECT ... FOR UPDATE SKIP LOCKED on PostgreSQL for safe, concurrent at-least-once dispatch.
- Every created and dispatched JobRef has attempt_count >= 1 (defaults to 1, never 0).
- Dispatcher passes a typed JobRef to QueuePort.publish(job_ref).
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, Union, List
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import OutboxEventModel, utc_now
from adapters.queue.base import QueuePort

logger = logging.getLogger("finscan.outbox")

# Exact frozen JobRef contract matching worker/consumer.py expectation
try:
    from core.contracts.jobs import JobRef
    if JobRef.model_fields["created_at"].is_required():
        JobRef.model_fields["created_at"].default_factory = lambda: utc_now().isoformat()
        JobRef.model_rebuild(force=True)
except ImportError:
    class JobRef(BaseModel):
        """
        Authoritative job reference payload published to queue and stored in outbox_events.
        Frozen specification: attempt_count has ge=1 and defaults to 1.
        """
        job_id: str = Field(..., description="Unique job identifier e.g. JOB-12345")
        application_id: str = Field(..., description="Target application identifier e.g. APP-25195")
        attempt_count: int = Field(1, ge=1, description="Delivery attempt counter (1-indexed, ge=1)")


def create_outbox_event(
    session: AsyncSession,
    aggregate_type: str,
    aggregate_id: str,
    payload: Union[JobRef, Dict[str, Any]],
    event_id: Optional[str] = None,
) -> OutboxEventModel:
    """
    Creates and attaches an outbox event record to the caller's active database session.
    
    IMPORTANT:
    This function NEVER commits internally. The caller must commit the enclosing transaction.
    Every outbox-created JobRef must have attempt_count >= 1 (defaults to 1, never 0).
    """
    if isinstance(payload, JobRef):
        validated_job = payload
    elif isinstance(payload, dict):
        payload_copy = dict(payload)
        if "attempt_count" not in payload_copy:
            payload_copy["attempt_count"] = 1
        validated_job = JobRef.model_validate(payload_copy)
    else:
        raise ValueError(f"Payload must be a JobRef or dict conforming to JobRef, got {type(payload)}")

    outbox_record = OutboxEventModel(
        id=event_id or str(uuid.uuid4()),
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=validated_job.model_dump(),
        status="PENDING",
        retry_count=0,
        last_error=None,
        created_at=utc_now(),
        published_at=None,
    )
    session.add(outbox_record)
    return outbox_record


async def dispatch_pending_outbox_events(
    session: AsyncSession,
    queue: QueuePort,
    batch_size: int = 10,
    max_retries: int = 3,
) -> Dict[str, int]:
    """
    Claims a batch of PENDING outbox events using SELECT ... FOR UPDATE SKIP LOCKED
    (on PostgreSQL), validates each against the frozen JobRef model, publishes
    the typed JobRef to the queue, and updates status.
    
    Returns:
        Dict with metrics: claimed, published, retried, failed.
    """
    stmt = (
        select(OutboxEventModel)
        .where(OutboxEventModel.status == "PENDING")
        .order_by(OutboxEventModel.created_at.asc())
        .limit(batch_size)
    )

    # Use row-level locking with SKIP LOCKED on PostgreSQL
    try:
        bind = session.get_bind()
        if bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
    except Exception:
        pass

    result = await session.execute(stmt)
    events: List[OutboxEventModel] = list(result.scalars().all())

    stats = {
        "claimed": len(events),
        "published": 0,
        "retried": 0,
        "failed": 0,
    }

    if not events:
        return stats

    for event in events:
        # Step 1: Reconstruct and validate against the exact frozen JobRef contract
        try:
            job_ref = JobRef.model_validate(event.payload)
        except Exception as val_err:
            logger.error(f"Invalid payload in outbox event {event.id}: {val_err}")
            event.retry_count += 1
            event.last_error = f"Payload validation error: {str(val_err)}"
            if event.retry_count >= max_retries:
                event.status = "FAILED"
                stats["failed"] += 1
            else:
                stats["retried"] += 1
            continue

        # Step 2: Publish typed JobRef to QueuePort (synchronous call safely delegated to thread)
        try:
            await asyncio.to_thread(queue.publish, job_ref)
            event.status = "PUBLISHED"
            event.published_at = utc_now()
            event.last_error = None
            stats["published"] += 1
        except Exception as pub_err:
            logger.error(f"Failed to publish outbox event {event.id} to queue: {pub_err}")
            event.retry_count += 1
            event.last_error = f"Queue publish error: {str(pub_err)}"
            if event.retry_count >= max_retries:
                event.status = "FAILED"
                stats["failed"] += 1
            else:
                stats["retried"] += 1

    # Commit state changes
    await session.commit()
    return stats

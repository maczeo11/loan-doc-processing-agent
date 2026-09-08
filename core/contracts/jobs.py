"""
JobRef: Authoritative job reference contract passed through outbox and queues.
Co-owned by Manjunath (Contracts) and Bhanu Teja (Worker & Queue Lead).
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class JobRef(BaseModel):
    """
    Standard payload emitted by API Transactional Outbox and consumed by Worker.
    """
    job_id: str = Field(..., description="Unique job identifier, e.g. JOB-550e8400-e29b-41d4-a716-446655440000")
    application_id: str = Field(..., description="Target loan application identifier, e.g. APP-25195")
    attempt_count: int = Field(default=1, ge=1, description="Delivery attempt counter (starts at 1; routed to DLQ if > 3)")
    created_at: str = Field(..., description="ISO 8601 UTC timestamp when the job was enqueued")
    priority: int = Field(default=0, ge=0, le=9, description="Priority level (0 = normal, 9 = urgent)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Trace context (e.g. trace_id, user_id, client_ip)")

"""
QueuePort: The 5-method port mandated by AGENTS.md.
"""

from typing import Protocol, List
from pydantic import BaseModel, Field
from core.contracts.jobs import JobRef


class Delivery(BaseModel):
    lease_handle: str = Field(..., description="Opaque lease handle used for ack, extend_lease, or fail")
    job_ref: JobRef = Field(..., description="Typed job reference payload")

    @property
    def handle(self) -> str:
        """Backward-compatible alias for lease_handle."""
        return self.lease_handle


class QueuePort(Protocol):
    def publish(self, job_ref: JobRef) -> None:
        ...

    def receive(self, max_n: int = 1) -> List[Delivery]:
        ...

    def extend_lease(self, handle: str, seconds: int) -> None:
        ...

    def ack(self, handle: str) -> None:
        ...

    def fail(self, handle: str, retryable: bool) -> None:
        ...

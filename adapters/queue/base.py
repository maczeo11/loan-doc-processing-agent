"""
QueuePort: The 5-method port mandated by AGENTS.md.
"""

from typing import Protocol, List, Any
from pydantic import BaseModel


class Delivery(BaseModel):
    handle: str  # Opaque lease handle
    payload: dict  # Job reference payload


class QueuePort(Protocol):
    def publish(self, job_ref: dict) -> None:
        ...

    def receive(self, max_n: int = 1) -> List[Delivery]:
        ...

    def extend_lease(self, handle: str, seconds: int) -> None:
        ...

    def ack(self, handle: str) -> None:
        ...

    def fail(self, handle: str, retryable: bool) -> None:
        ...

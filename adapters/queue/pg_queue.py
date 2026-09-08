"""
PostgreSQL SKIP LOCKED queue adapter for local development.
"""

from typing import List, Optional
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef


class PostgresQueue(QueuePort):
    def __init__(self, connection_string: Optional[str] = None, dsn: Optional[str] = None):
        self.dsn = connection_string or dsn or "postgresql://finscan:finscan@localhost:5432/finscan"

    def publish(self, job_ref: JobRef) -> None:
        # Member 6 implement transactional outbox / job enqueue
        pass

    def receive(self, max_n: int = 1) -> List[Delivery]:
        # Member 2 & 6 implement SELECT ... FOR UPDATE SKIP LOCKED
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        pass

    def fail(self, handle: str, retryable: bool) -> None:
        pass


# Alias for backward compatibility
PostgresQueueAdapter = PostgresQueue

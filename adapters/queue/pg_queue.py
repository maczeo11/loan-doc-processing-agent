"""
PostgreSQL SKIP LOCKED queue adapter for local development.
"""

from typing import List
from adapters.queue.base import QueuePort, Delivery


class PostgresQueue(QueuePort):
    def __init__(self, dsn: str = "postgresql://finscan:finscan@localhost:5432/finscan"):
        self.dsn = dsn

    def publish(self, job_ref: dict) -> None:
        # TODO: Member 6 implement transactional outbox / job enqueue
        pass

    def receive(self, max_n: int = 1) -> List[Delivery]:
        # TODO: Member 2 & 6 implement SELECT ... FOR UPDATE SKIP LOCKED
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        pass

    def fail(self, handle: str, retryable: bool) -> None:
        pass

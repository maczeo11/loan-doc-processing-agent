"""
AWS SQS + DLQ queue adapter for cloud demo deployment.
"""

from typing import List, Optional
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef


class SQSQueue(QueuePort):
    def __init__(self, queue_url: str = "", dlq_url: str = "", region_name: str = "us-east-1", region: Optional[str] = None):
        self.queue_url = queue_url
        self.dlq_url = dlq_url
        self.region = region or region_name

    def publish(self, job_ref: JobRef) -> None:
        # Member 2 & 6 implement SQS send_message
        pass

    def receive(self, max_n: int = 1) -> List[Delivery]:
        # Member 2 implement SQS receive_message with VisibilityTimeout
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        pass

    def fail(self, handle: str, retryable: bool) -> None:
        pass


# Alias for backward compatibility
SQSQueueAdapter = SQSQueue

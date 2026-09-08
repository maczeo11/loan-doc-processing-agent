"""
AWS SQS + DLQ queue adapter for cloud demo deployment.
"""

from typing import List
from adapters.queue.base import QueuePort, Delivery


class SQSQueue(QueuePort):
    def __init__(self, queue_url: str, dlq_url: str, region: str = "us-east-1"):
        self.queue_url = queue_url
        self.dlq_url = dlq_url
        self.region = region

    def publish(self, job_ref: dict) -> None:
        # TODO: Member 2 & 6 implement SQS send_message
        pass

    def receive(self, max_n: int = 1) -> List[Delivery]:
        # TODO: Member 2 implement SQS receive_message with VisibilityTimeout
        return []

    def extend_lease(self, handle: str, seconds: int) -> None:
        pass

    def ack(self, handle: str) -> None:
        pass

    def fail(self, handle: str, retryable: bool) -> None:
        pass

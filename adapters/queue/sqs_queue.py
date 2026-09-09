"""
AWS SQS + DLQ queue adapter for cloud demo deployment.
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Implements:
- SQS message publishing with JobRef JSON serialization
- SQS message consumption with VisibilityTimeout leases
- LeaseHeartbeat extension via change_message_visibility
- Acknowledge via delete_message
- Retryable redelivery via visibility reset (timeout=0)
- Dead Letter Queue (DLQ) routing for non-retryable failures
"""

import logging
from typing import List, Optional, Any
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef

logger = logging.getLogger("finscan.adapters.queue.sqs")


class SQSQueue(QueuePort):
    """
    AWS SQS + DLQ QueuePort adapter for production/cloud deployment.
    """

    def __init__(
        self,
        queue_url: str = "",
        dlq_url: str = "",
        region_name: str = "us-east-1",
        region: Optional[str] = None,
        sqs_client: Optional[Any] = None,
    ):
        self.queue_url = queue_url
        self.dlq_url = dlq_url
        self.region = region or region_name
        self._client = sqs_client

    @property
    def client(self):
        """Lazily initialize boto3 client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("sqs", region_name=self.region)
            except Exception as e:
                logger.error(f"Failed to initialize boto3 SQS client: {e}")
                raise
        return self._client

    def publish(self, job_ref: JobRef) -> None:
        """Sends a job message to the primary SQS queue."""
        if not self.queue_url:
            raise ValueError("SQS queue_url is not configured.")

        body = job_ref.model_dump_json()
        response = self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=body,
            MessageAttributes={
                "job_id": {"DataType": "String", "StringValue": job_ref.job_id},
                "application_id": {"DataType": "String", "StringValue": job_ref.application_id},
                "priority": {"DataType": "Number", "StringValue": str(job_ref.priority)},
            },
        )
        logger.info(f"Published job {job_ref.job_id} to SQS (MessageId={response.get('MessageId')})")

    def receive(self, max_n: int = 1, visibility_timeout: int = 30) -> List[Delivery]:
        """
        Receives messages from SQS with a visibility timeout lease.
        Synchronizes attempt_count from SQS ApproximateReceiveCount attribute.
        """
        if not self.queue_url:
            return []

        try:
            response = self.client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=min(max(max_n, 1), 10),
                VisibilityTimeout=visibility_timeout,
                AttributeNames=["ApproximateReceiveCount"],
                MessageAttributeNames=["All"],
            )

            messages = response.get("Messages", [])
            deliveries: List[Delivery] = []

            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                body_str = msg["Body"]
                job_ref = JobRef.model_validate_json(body_str)

                # Sync attempt count from SQS delivery metadata
                attrs = msg.get("Attributes", {})
                if "ApproximateReceiveCount" in attrs:
                    job_ref.attempt_count = int(attrs["ApproximateReceiveCount"])

                deliveries.append(Delivery(lease_handle=receipt_handle, job_ref=job_ref))

            return deliveries
        except Exception as e:
            logger.error(f"Failed to receive messages from SQS {self.queue_url}: {e}")
            return []

    def extend_lease(self, handle: str, seconds: int = 30) -> None:
        """Extends message visibility timeout in SQS."""
        if not self.queue_url:
            return

        try:
            self.client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=handle,
                VisibilityTimeout=seconds,
            )
            logger.debug(f"Extended SQS lease for handle {handle[:16]}... by {seconds}s")
        except Exception as e:
            logger.warning(f"Failed to extend SQS lease: {e}")

    def ack(self, handle: str) -> None:
        """Deletes processed message from primary SQS queue."""
        if not self.queue_url:
            return

        try:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=handle,
            )
            logger.info(f"Acknowledged SQS message {handle[:16]}...")
        except Exception as e:
            logger.error(f"Failed to delete SQS message {handle[:16]}: {e}")

    def fail(self, handle: str, retryable: bool) -> None:
        """
        Handles message processing failure:
        - If retryable: resets VisibilityTimeout to 0 to trigger immediate retry.
        - If not retryable: routes message to DLQ (if configured) and deletes from primary queue.
        """
        if not self.queue_url:
            return

        try:
            if retryable:
                # Immediate redelivery
                self.client.change_message_visibility(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=handle,
                    VisibilityTimeout=0,
                )
                logger.warning(f"Reset visibility timeout to 0 for retry of {handle[:16]}...")
            else:
                # Non-retryable: send to DLQ if configured, then ack from main queue
                if self.dlq_url:
                    logger.warning(f"Routing poisonous message {handle[:16]}... to DLQ {self.dlq_url}")
                    self.client.send_message(
                        QueueUrl=self.dlq_url,
                        MessageBody=f'{{"failed_handle": "{handle}", "reason": "Max attempts exceeded"}}',
                    )
                self.client.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=handle,
                )
                logger.info(f"Removed poisonous message {handle[:16]}... from primary queue")
        except Exception as e:
            logger.error(f"Error handling failure for SQS handle {handle[:16]}: {e}")


# Alias for backward compatibility
SQSQueueAdapter = SQSQueue


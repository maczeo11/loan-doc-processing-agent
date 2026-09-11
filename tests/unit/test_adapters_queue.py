"""
Unit tests for PostgresQueue and SQSQueue adapters.
Owned by Member 2 (Bhanu Teja).

Verifies:
- PostgresQueue: SKIP LOCKED atomic claims, lease extension, ack, and retryable/non-retryable fail.
- SQSQueue: Visibility timeout lease management, ack delete_message, retryable reset, and DLQ routing.
"""

from unittest.mock import MagicMock
from core.contracts.jobs import JobRef
from adapters.queue.pg_queue import PostgresQueue
from adapters.queue.sqs_queue import SQSQueue


def sample_job_ref(app_id: str = "APP-TEST-QUEUE", attempt_count: int = 1) -> JobRef:
    return JobRef(
        job_id=f"JOB-{app_id}",
        application_id=app_id,
        attempt_count=attempt_count,
        created_at="2026-09-08T12:00:00Z",
        priority=0,
        metadata={"document_ids": ["doc1", "doc2"]},
    )


class MockCursor:
    def __init__(self, fetchall_data=None):
        self.executed_queries = []
        self.fetchall_data = fetchall_data or []

    def execute(self, query, params=None):
        self.executed_queries.append((query, params))

    def fetchall(self):
        return self.fetchall_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockConnection:
    def __init__(self, cursor=None):
        self.cursor_obj = cursor or MockCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


# =====================================================================
# PostgresQueue Tests
# =====================================================================

def test_postgres_queue_publish():
    cur = MockCursor()
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)
    job = sample_job_ref()

    queue.publish(job)

    assert len(cur.executed_queries) == 1
    query, params = cur.executed_queries[0]
    assert "INSERT INTO outbox_jobs" in query
    assert params[0] == job.job_id
    assert params[1] == job.application_id
    assert conn.committed is True


def test_postgres_queue_receive_skip_locked():
    job = sample_job_ref()
    cur = MockCursor(fetchall_data=[(job.job_id, job.model_dump_json(), 0)])
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)

    deliveries = queue.receive(max_n=1, visibility_seconds=30)

    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery.lease_handle == job.job_id
    assert delivery.job_ref.job_id == job.job_id
    assert delivery.job_ref.application_id == job.application_id
    assert delivery.job_ref.attempt_count == 1

    query, params = cur.executed_queries[0]
    assert "FOR UPDATE SKIP LOCKED" in query
    assert conn.committed is True


def test_postgres_queue_receive_escalates_attempt_from_retry_count():
    """Poison messages must surface attempt = retries + 1 so the consumer DLQ ceiling trips."""
    job = sample_job_ref()
    cur = MockCursor(fetchall_data=[(job.job_id, job.model_dump_json(), 3)])
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)

    deliveries = queue.receive(max_n=1)

    assert len(deliveries) == 1
    assert deliveries[0].job_ref.attempt_count == 4


def test_postgres_queue_extend_lease():
    cur = MockCursor()
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)

    queue.extend_lease("JOB-123", seconds=45)

    assert len(cur.executed_queries) == 1
    query, params = cur.executed_queries[0]
    assert "UPDATE outbox_jobs" in query
    assert "locked_until" in query
    assert params == ("45", "JOB-123")
    assert conn.committed is True


def test_postgres_queue_ack():
    cur = MockCursor()
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)

    queue.ack("JOB-123")

    assert len(cur.executed_queries) == 1
    query, params = cur.executed_queries[0]
    assert "SET status = 'COMPLETED'" in query
    assert params == ("JOB-123",)
    assert conn.committed is True


def test_postgres_queue_fail_retryable_vs_dlq():
    cur = MockCursor()
    conn = MockConnection(cur)
    queue = PostgresQueue(table_name="outbox_jobs", conn=conn)

    # Retryable fail resets status to PENDING
    queue.fail("JOB-123", retryable=True)
    assert cur.executed_queries[0][1][0] == "PENDING"

    # Non-retryable fail sets status to FAILED (DLQ)
    queue.fail("JOB-123", retryable=False)
    assert cur.executed_queries[1][1][0] == "FAILED"


# =====================================================================
# SQSQueue Tests
# =====================================================================

def test_sqs_queue_publish():
    mock_boto = MagicMock()
    mock_boto.send_message.return_value = {"MessageId": "msg-123"}
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan", sqs_client=mock_boto)
    job = sample_job_ref()

    queue.publish(job)

    mock_boto.send_message.assert_called_once()
    call_kwargs = mock_boto.send_message.call_args[1]
    assert call_kwargs["QueueUrl"] == "https://sqs.us-east-1.amazonaws.com/123/finscan"
    assert job.job_id in call_kwargs["MessageBody"]


def test_sqs_queue_receive():
    job = sample_job_ref(attempt_count=2)
    mock_boto = MagicMock()
    mock_boto.receive_message.return_value = {
        "Messages": [
            {
                "ReceiptHandle": "receipt-abc",
                "Body": job.model_dump_json(),
                "Attributes": {"ApproximateReceiveCount": "2"},
            }
        ]
    }
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan", sqs_client=mock_boto)

    deliveries = queue.receive(max_n=1)

    assert len(deliveries) == 1
    assert deliveries[0].lease_handle == "receipt-abc"
    assert deliveries[0].job_ref.job_id == job.job_id
    assert deliveries[0].job_ref.attempt_count == 2


def test_sqs_queue_extend_lease():
    mock_boto = MagicMock()
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan", sqs_client=mock_boto)

    queue.extend_lease("receipt-abc", seconds=45)

    mock_boto.change_message_visibility.assert_called_once_with(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/123/finscan",
        ReceiptHandle="receipt-abc",
        VisibilityTimeout=45,
    )


def test_sqs_queue_ack():
    mock_boto = MagicMock()
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan", sqs_client=mock_boto)

    queue.ack("receipt-abc")

    mock_boto.delete_message.assert_called_once_with(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/123/finscan",
        ReceiptHandle="receipt-abc",
    )


def test_sqs_queue_fail_retryable():
    mock_boto = MagicMock()
    queue = SQSQueue(queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan", sqs_client=mock_boto)

    # Retryable failure backs the message off rather than redelivering immediately.
    # VisibilityTimeout=0 would hot-loop a poison message through its 3 attempts
    # in milliseconds, defeating the DLQ ceiling; 30s spaces the retries out.
    queue.fail("receipt-abc", retryable=True)

    mock_boto.change_message_visibility.assert_called_once_with(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/123/finscan",
        ReceiptHandle="receipt-abc",
        VisibilityTimeout=30,
    )


def test_sqs_queue_fail_poison_routes_to_dlq():
    mock_boto = MagicMock()
    queue = SQSQueue(
        queue_url="https://sqs.us-east-1.amazonaws.com/123/finscan",
        dlq_url="https://sqs.us-east-1.amazonaws.com/123/finscan-dlq",
        sqs_client=mock_boto,
    )

    # Non-retryable failure routes to DLQ and deletes from main queue
    queue.fail("receipt-abc", retryable=False)

    mock_boto.send_message.assert_called_once_with(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/123/finscan-dlq",
        MessageBody='{"failed_handle": "receipt-abc", "reason": "Max attempts exceeded"}',
    )
    mock_boto.delete_message.assert_called_once_with(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/123/finscan",
        ReceiptHandle="receipt-abc",
    )

"""
Worker entrypoint process.

Initializes selected queue adapter (Postgres SKIP LOCKED or AWS SQS),
selected storage adapter (Local filesystem or AWS S3),
and starts consumer.
"""

import os
import sys
import logging
from adapters.queue.pg_queue import PostgresQueueAdapter
from adapters.queue.sqs_queue import SQSQueueAdapter
from core.graph.checkpoint import SqliteSaver
from worker.consumer import ApplicationWorker

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finscan.worker.main")


def main():
    queue_backend = os.getenv("QUEUE_BACKEND", "postgres")
    logger.info(f"Starting FinScan Worker with queue backend: {queue_backend}")

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/finscan")

    if queue_backend == "sqs":
        queue_url = os.getenv("SQS_QUEUE_URL", "")
        region = os.getenv("AWS_REGION", "us-east-1")
        # Without dlq_url the worker deletes poison messages from the primary
        # queue with no DLQ record, and SQS RedrivePolicy never fires because
        # the delete beats maxReceiveCount.
        dlq_url = os.getenv("SQS_DLQ_URL", "")
        if not dlq_url:
            logger.warning(
                "SQS_DLQ_URL is not set: poison messages will be dropped without a dead-letter record."
            )
        queue_adapter = SQSQueueAdapter(queue_url=queue_url, dlq_url=dlq_url, region_name=region)
    else:
        queue_adapter = PostgresQueueAdapter(connection_string=db_url)
        queue_adapter.ensure_schema()

    # Storage adapter: S3 for cloud, local filesystem for local/demo
    storage_backend = os.getenv("STORAGE_BACKEND", "local")
    logger.info(f"Initializing storage adapter: {storage_backend}")

    if storage_backend == "s3":
        from adapters.storage.s3 import S3Storage
        bucket = os.getenv("S3_BUCKET", "finscan-dossiers-production")
        region = os.getenv("AWS_REGION", "us-east-1")
        storage_adapter = S3Storage(bucket_name=bucket, region_name=region)
    else:
        from adapters.storage.local_fs import LocalFileSystemStorage
        base_dir = os.getenv("STORAGE_BASE_DIR", "data/storage")
        storage_adapter = LocalFileSystemStorage(base_dir=base_dir)

    checkpoint_db = os.getenv("CHECKPOINT_DB_PATH", "data/storage/checkpoints.sqlite3")
    checkpointer = SqliteSaver(db_path=checkpoint_db)

    worker = ApplicationWorker(
        queue_adapter=queue_adapter,
        storage_adapter=storage_adapter,
        checkpointer=checkpointer,
        db_url=db_url,
    )

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
        worker.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()


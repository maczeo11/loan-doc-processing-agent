"""
Worker entrypoint process.

Initializes selected queue adapter (Postgres SKIP LOCKED or AWS SQS) and starts consumer.
"""

import os
import sys
import logging
from adapters.queue.pg_queue import PostgresQueueAdapter
from adapters.queue.sqs_queue import SQSQueueAdapter
from core.graph.checkpoint import SqliteSaver
from worker.consumer import ApplicationWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finscan.worker.main")


def main():
    queue_backend = os.getenv("QUEUE_BACKEND", "postgres")
    logger.info(f"Starting FinScan Worker with queue backend: {queue_backend}")

    if queue_backend == "sqs":
        queue_url = os.getenv("SQS_QUEUE_URL", "")
        region = os.getenv("AWS_REGION", "us-east-1")
        queue_adapter = SQSQueueAdapter(queue_url=queue_url, region_name=region)
    else:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgrespassword@localhost:5432/finscan")
        queue_adapter = PostgresQueueAdapter(connection_string=db_url)
        queue_adapter.ensure_schema()

    checkpoint_db = os.getenv("CHECKPOINT_DB_PATH", "data/storage/checkpoints.sqlite3")
    checkpointer = SqliteSaver(db_path=checkpoint_db)
    worker = ApplicationWorker(queue_adapter=queue_adapter, checkpointer=checkpointer)

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
        worker.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()

"""
Standalone Transactional Outbox Dispatcher service for FinScan AI.

Polls PENDING outbox_events table using SELECT ... FOR UPDATE SKIP LOCKED
and reliably forwards them to the configured QueuePort (Postgres or AWS SQS).
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from apps.api.config import settings
from apps.api.db.session import async_session_factory
from apps.api.db.outbox import dispatch_pending_outbox_events
from adapters.queue.base import QueuePort
from adapters.queue.pg_queue import PostgresQueue
from adapters.queue.sqs_queue import SQSQueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("finscan.outbox_dispatcher")


def get_queue_adapter() -> QueuePort:
    """Instantiate configured QueuePort adapter."""
    if settings.QUEUE_BACKEND == "sqs":
        logger.info("Initializing SQSQueue adapter for outbox dispatcher.")
        return SQSQueue(
            queue_url=settings.SQS_QUEUE_URL,
            dlq_url="",
            region=settings.AWS_REGION,
        )
    else:
        logger.info("Initializing PostgresQueue adapter for outbox dispatcher.")
        return PostgresQueue(dsn=settings.DATABASE_URL)


async def run_dispatcher_loop(
    queue: Optional[QueuePort] = None,
    poll_interval: float = 1.0,
    batch_size: int = 10,
    max_retries: int = 3,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """
    Continuous outbox dispatch loop.
    """
    queue_adapter = queue or get_queue_adapter()
    stop = stop_event or asyncio.Event()

    logger.info("Starting FinScan Outbox Dispatcher loop...")

    while not stop.is_set():
        try:
            async with async_session_factory() as session:
                stats = await dispatch_pending_outbox_events(
                    session=session,
                    queue=queue_adapter,
                    batch_size=batch_size,
                    max_retries=max_retries,
                )

                if stats["claimed"] > 0:
                    logger.info(
                        f"Dispatched outbox batch: claimed={stats['claimed']}, "
                        f"published={stats['published']}, retried={stats['retried']}, failed={stats['failed']}"
                    )
                else:
                    # No pending events, wait poll interval
                    await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Outbox dispatcher task cancelled.")
            break
        except Exception as err:
            logger.error(f"Error in outbox dispatcher cycle: {err}", exc_info=True)
            await asyncio.sleep(poll_interval)

    logger.info("Outbox Dispatcher stopped.")


def main():
    """Main CLI entrypoint."""
    stop_event = asyncio.Event()

    def handle_signal(*args):
        logger.info("Signal received, stopping dispatcher...")
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(run_dispatcher_loop(stop_event=stop_event))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Outbox dispatcher exited.")


if __name__ == "__main__":
    main()

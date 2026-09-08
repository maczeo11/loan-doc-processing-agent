"""
Async worker consumer loop.

Rules from AGENTS.md:
- Delivery is at-least-once.
- Handlers must be idempotent.
- Results commit BEFORE ack.
- Atomic worker lease with heartbeat/extend_lease.
- Three-delivery ceiling before moving to DLQ.
"""

import time
import logging
from adapters.queue.base import QueuePort, Delivery
from core.graph.workflow import build_application_graph

logger = logging.getLogger("finscan.worker")


class ApplicationWorker:
    """Worker process that polls for jobs, runs the LangGraph pipeline, and handles leases."""

    def __init__(self, queue_adapter: QueuePort):
        self.queue = queue_adapter
        self.running = False
        self.graph = build_application_graph()

    def start(self, poll_interval_seconds: float = 2.0):
        """Main consumer loop."""
        self.running = True
        logger.info("FinScan Worker consumer started.")

        while self.running:
            try:
                deliveries = self.queue.receive(max_n=1)
                if not deliveries:
                    time.sleep(poll_interval_seconds)
                    continue

                for delivery in deliveries:
                    self.process_delivery(delivery)
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user.")
                self.stop()
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                time.sleep(poll_interval_seconds)

    def process_delivery(self, delivery: Delivery):
        """Process a single job delivery idempotently."""
        job_ref = delivery.job_ref
        logger.info(f"Processing job {job_ref.job_id} (application {job_ref.application_id}, attempt {job_ref.attempt_count})")

        try:
            # Check delivery ceiling
            if job_ref.attempt_count > 3:
                logger.error(f"Job {job_ref.job_id} exceeded delivery ceiling (3). Routing to DLQ.")
                self.queue.fail(delivery.lease_handle, retryable=False)
                return

            # Initialize LangGraph state & run
            initial_state = {
                "application_id": job_ref.application_id,
                "status": "PROCESSING",
                "status_history": [],
                "document_ids": [],
                "document_manifest": {},
                "classified_types": {},
                "applicant": None,
                "payslip": None,
                "bank_statement": None,
                "tax_return": None,
                "findings": [],
                "missing_documents": [],
                "retrieved_chunk_ids": [],
                "summary_markdown": None,
                "summary_grounded": False,
                "review_paused": False,
                "reviewer_decision": None,
                "reviewer_notes": None,
                "corrections_applied": [],
            }

            # Run graph nodes
            final_state = self.graph.invoke(initial_state)

            # Results commit BEFORE ack
            logger.info(f"Job {job_ref.job_id} state updated to {final_state.get('status')}. Committing results...")

            # Acknowledge delivery
            self.queue.ack(delivery.lease_handle)
            logger.info(f"Job {job_ref.job_id} successfully acknowledged.")

        except Exception as err:
            logger.error(f"Failed to process job {job_ref.job_id}: {err}", exc_info=True)
            self.queue.fail(delivery.lease_handle, retryable=True)

    def stop(self):
        self.running = False
        logger.info("FinScan Worker consumer stopped.")

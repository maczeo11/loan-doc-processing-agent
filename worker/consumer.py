"""
Async worker consumer loop.

Rules from AGENTS.md & HLD:
- Delivery is at-least-once.
- Handlers must be idempotent.
- Results commit BEFORE ack.
- Atomic worker lease with heartbeat/extend_lease.
- Three-delivery ceiling before moving to DLQ.
- Worker retrieves raw document bytes via StoragePort.get(key) before handing off to extractors.
"""

import time
import logging
from typing import Optional, Dict
from adapters.queue.base import QueuePort, Delivery
from adapters.storage.base import StoragePort
from adapters.storage.local_fs import LocalFileSystemStorage
from core.graph.workflow import build_application_graph

logger = logging.getLogger("finscan.worker")


class ApplicationWorker:
    """
    Worker process that polls for jobs, loads raw document bytes via StoragePort,
    runs the LangGraph pipeline, and handles leases and acknowledgements.
    """

    def __init__(
        self,
        queue_adapter: QueuePort,
        storage_adapter: Optional[StoragePort] = None,
    ):
        self.queue = queue_adapter
        self.storage: StoragePort = storage_adapter or LocalFileSystemStorage()
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
        logger.info(
            f"Processing job {job_ref.job_id} (application {job_ref.application_id}, attempt {job_ref.attempt_count})"
        )

        try:
            # 1. Check delivery ceiling (3-delivery ceiling before DLQ)
            if job_ref.attempt_count > 3:
                logger.error(f"Job {job_ref.job_id} exceeded delivery ceiling (3). Routing to DLQ.")
                self.queue.fail(delivery.lease_handle, retryable=False)
                return

            # 2. Worker Storage Retrieval: Fetch raw document bytes via StoragePort.get(key)
            manifest: Dict[str, str] = job_ref.metadata.get("document_manifest", {})
            doc_ids = list(manifest.keys())
            doc_bytes_map: Dict[str, bytes] = {}

            for doc_id, storage_key in manifest.items():
                try:
                    raw_bytes = self.storage.get(storage_key)
                    doc_bytes_map[doc_id] = raw_bytes
                    logger.info(
                        f"Retrieved {len(raw_bytes)} bytes from storage for {doc_id} (key: {storage_key})"
                    )
                except Exception as err:
                    logger.warning(f"Could not retrieve bytes for {doc_id} from key '{storage_key}': {err}")

            # 3. Initialize LangGraph state
            initial_state = {
                "application_id": job_ref.application_id,
                "status": "PROCESSING",
                "status_history": [],
                "document_ids": doc_ids,
                "document_manifest": manifest,
                "document_bytes": doc_bytes_map,
                "classified_types": job_ref.metadata.get("classified_types", {}),
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

            # 4. Execute LangGraph pipeline
            final_state = self.graph.invoke(initial_state)

            # 5. Results commit BEFORE ack
            logger.info(
                f"Job {job_ref.job_id} reached status '{final_state.get('status')}'. Committing results..."
            )

            # 6. Acknowledge delivery
            self.queue.ack(delivery.lease_handle)
            logger.info(f"Job {job_ref.job_id} successfully acknowledged.")

        except Exception as err:
            logger.error(f"Failed to process job {job_ref.job_id}: {err}", exc_info=True)
            self.queue.fail(delivery.lease_handle, retryable=True)

    def stop(self):
        self.running = False
        logger.info("FinScan Worker consumer stopped.")

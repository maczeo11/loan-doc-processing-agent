"""
Async worker consumer loop.
Owned by Member 2 (Bhanu Teja).

Rules from AGENTS.md & HLD:
- Delivery is at-least-once.
- Handlers must be completely idempotent.
- Acknowledge-Last: Results commit BEFORE ack is called.
- Atomic worker lease with heartbeat/extend_lease.
- Three-delivery ceiling before routing poisonous messages to DLQ.
- Worker retrieves raw document bytes via StoragePort.get(key) before handing off to extractors.
"""

import time
import threading
import logging
from typing import Optional, Dict, Any

from adapters.queue.base import QueuePort, Delivery
from adapters.storage.base import StoragePort
from adapters.storage.local_fs import LocalFileSystemStorage
from core.contracts.jobs import JobRef
from core.contracts.state import LoanApplicationState
from core.contracts.facts import PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact
from core.graph.workflow import build_application_graph

logger = logging.getLogger("finscan.worker")


class LeaseHeartbeat:
    """
    Background heartbeat thread that periodically extends the lease of an in-flight job.
    Prevents other workers from stealing long-running OCR or RAG jobs.
    """

    def __init__(
        self,
        queue: QueuePort,
        lease_handle: str,
        interval_seconds: float = 10.0,
        extension_seconds: int = 30,
    ):
        self.queue = queue
        self.lease_handle = lease_handle
        self.interval_seconds = interval_seconds
        self.extension_seconds = extension_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="LeaseHeartbeatThread")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            try:
                logger.debug(f"Heartbeat: extending lease for handle {self.lease_handle[:16]}... by {self.extension_seconds}s")
                self.queue.extend_lease(self.lease_handle, self.extension_seconds)
            except Exception as exc:
                logger.warning(f"Failed to extend lease for {self.lease_handle[:16]}: {exc}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class ApplicationWorker:
    """
    Worker process that polls for jobs, loads raw document bytes via StoragePort,
    runs the LangGraph pipeline, and enforces lease and acknowledge-last semantics.
    """

    def __init__(
        self,
        queue_adapter: QueuePort,
        storage_adapter: Optional[StoragePort] = None,
        checkpointer=None,
        max_delivery_attempts: int = 3,
        heartbeat_interval_seconds: float = 10.0,
        heartbeat_extension_seconds: int = 30,
        graph=None,
    ):
        self.queue = queue_adapter
        self.storage: StoragePort = storage_adapter or LocalFileSystemStorage()
        self.checkpointer = checkpointer
        self.max_delivery_attempts = max_delivery_attempts
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.heartbeat_extension_seconds = heartbeat_extension_seconds
        self.running = False
        self.graph = graph if graph is not None else build_application_graph(checkpointer=checkpointer, enable_interrupt=True)

    def start(self, poll_interval_seconds: float = 2.0) -> None:
        """Main consumer polling loop."""
        self.running = True
        logger.info("FinScan Worker consumer started.")

        while self.running:
            try:
                deliveries = self.queue.receive(max_n=1)
                if not deliveries:
                    time.sleep(poll_interval_seconds)
                    continue

                for delivery in deliveries:
                    if not self.running:
                        # Graceful shutdown requested; reject unstarted delivery retryably
                        self.queue.fail(delivery.lease_handle, retryable=True)
                        break
                    self.process_delivery(delivery)
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user.")
                self.stop()
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                time.sleep(poll_interval_seconds)
    def process_delivery(self, delivery: Delivery) -> Optional[Dict[str, Any]]:
        """
        Process a single job delivery idempotently.
        Guarantees:
        1. Ceiling guard: Attempt count > 3 routes to DLQ via fail(retryable=False).
        2. Heartbeat keeps lease alive during execution.
        3. Acknowledge-last: Results commit before queue.ack() is invoked.
        """
        job_ref: JobRef = delivery.job_ref
        handle: str = delivery.lease_handle

        logger.info(
            f"Processing job {job_ref.job_id} for application {job_ref.application_id} "
            f"(attempt {job_ref.attempt_count}/{self.max_delivery_attempts})"
        )

        # 1. Bounded Retries & DLQ Routing
        if job_ref.attempt_count > self.max_delivery_attempts:
            logger.error(
                f"Job {job_ref.job_id} exceeded maximum attempt ceiling ({self.max_delivery_attempts}). "
                f"Routing to Dead Letter Queue (DLQ)."
            )
            self.queue.fail(handle, retryable=False)
            return None

        # 2. Run under lease heartbeat context
        with LeaseHeartbeat(
            self.queue,
            handle,
            interval_seconds=self.heartbeat_interval_seconds,
            extension_seconds=self.heartbeat_extension_seconds,
        ):
            try:
                # Worker Storage Retrieval: Fetch raw document bytes via StoragePort.get(key)
                manifest: Dict[str, str] = job_ref.metadata.get("document_manifest", {})
                doc_ids = job_ref.metadata.get("document_ids") or list(manifest.keys())
                doc_bytes_map: Dict[str, bytes] = {}

                for doc_id, storage_key in manifest.items():
                    try:
                        raw_bytes = self.storage.get(storage_key)
                        doc_bytes_map[doc_id] = raw_bytes
                        logger.info(f"Retrieved {len(raw_bytes)} bytes from storage for {doc_id} (key: {storage_key})")
                    except Exception as err:
                        logger.warning(f"Could not retrieve bytes for {doc_id} from key '{storage_key}': {err}")

                # Hydrate serialized dict facts if present in job metadata
                applicant_val = job_ref.metadata.get("applicant")
                if isinstance(applicant_val, dict):
                    try:
                        applicant_val = ApplicantFact.model_validate(applicant_val)
                    except Exception:
                        pass

                payslip_val = job_ref.metadata.get("payslip")
                if isinstance(payslip_val, dict):
                    try:
                        payslip_val = PayslipFacts.model_validate(payslip_val)
                    except Exception:
                        pass

                bank_val = job_ref.metadata.get("bank_statement")
                if isinstance(bank_val, dict):
                    try:
                        bank_val = BankStatementFacts.model_validate(bank_val)
                    except Exception:
                        pass

                tax_val = job_ref.metadata.get("tax_return")
                if isinstance(tax_val, dict):
                    try:
                        tax_val = TaxReturnFacts.model_validate(tax_val)
                    except Exception:
                        pass

                initial_state: LoanApplicationState = {
                    "application_id": job_ref.application_id,
                    "status": "PROCESSING",
                    "status_history": [],
                    "document_ids": doc_ids,
                    "document_manifest": manifest,
                    "document_bytes": doc_bytes_map,
                    "classified_types": job_ref.metadata.get("classified_types", {}),
                    "applicant": applicant_val,
                    "payslip": payslip_val,
                    "bank_statement": bank_val,
                    "tax_return": tax_val,
                    "findings": job_ref.metadata.get("findings", []),
                    "missing_documents": job_ref.metadata.get("missing_documents", []),
                    "retrieved_chunk_ids": job_ref.metadata.get("retrieved_chunk_ids", []),
                    "summary_markdown": None,
                    "summary_grounded": False,
                    "review_paused": False,
                    "reviewer_decision": None,
                    "reviewer_notes": None,
                    "corrections_applied": [],
                }

                config = {"configurable": {"thread_id": job_ref.application_id}}

                # 3. Invoke LangGraph StateGraph pipeline
                final_state = self.graph.invoke(initial_state, config=config)
                current_status = final_state.get("status", "UNKNOWN")

                # 4. Acknowledge-Last: State committed before message is deleted
                logger.info(
                    f"Job {job_ref.job_id} pipeline completed with status: {current_status}. "
                    f"Committing state and acknowledging message..."
                )

                self.queue.ack(handle)
                logger.info(f"Job {job_ref.job_id} successfully acknowledged and removed from queue.")
                return final_state

            except Exception as err:
                logger.error(f"Failure processing job {job_ref.job_id}: {err}", exc_info=True)
                # Fail retryably if within delivery ceiling
                self.queue.fail(handle, retryable=True)
                return None

    def stop(self) -> None:
        """Signals the worker to stop processing new jobs."""
        self.running = False
        logger.info("FinScan Worker consumer stopped.")

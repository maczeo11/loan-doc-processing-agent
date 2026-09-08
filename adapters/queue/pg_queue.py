"""
PostgreSQL SKIP LOCKED queue adapter for local development and worker consumer.
Owned by Member 2 (Bhanu Teja) & Member 6 (Balaji).

Implements atomic lease claims using:
    SELECT ... FOR UPDATE SKIP LOCKED
and single-statement atomic claim updates:
    WITH claimed AS (...) UPDATE ... RETURNING ...
"""

import json
import logging
from typing import List, Optional, Any
from adapters.queue.base import QueuePort, Delivery
from core.contracts.jobs import JobRef

logger = logging.getLogger("finscan.adapters.queue.postgres")

try:
    import psycopg as pg_driver
except ImportError:
    try:
        import psycopg2 as pg_driver
    except ImportError:
        pg_driver = None


class PostgresQueue(QueuePort):
    """
    PostgreSQL QueuePort adapter using the outbox_jobs table with SKIP LOCKED.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        dsn: Optional[str] = None,
        table_name: str = "outbox_jobs",
        conn: Optional[Any] = None,
    ):
        self.dsn = connection_string or dsn or "postgresql://postgres:postgrespassword@localhost:5432/finscan"
        self.table_name = table_name
        self._conn = conn

    def _get_connection(self):
        if self._conn is not None:
            return self._conn
        if pg_driver is None:
            raise RuntimeError("Neither 'psycopg' nor 'psycopg2' is installed. Cannot connect to PostgreSQL.")
        return pg_driver.connect(self.dsn)

    def ensure_schema(self) -> None:
        """Ensures outbox_jobs table and indexes exist."""
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_id VARCHAR(64) UNIQUE NOT NULL,
            application_id VARCHAR(64) NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            retry_count INT NOT NULL DEFAULT 0,
            locked_until TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            dispatched_at TIMESTAMPTZ NULL,
            completed_at TIMESTAMPTZ NULL
        );
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_app_id ON {self.table_name} (application_id);
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_status_created ON {self.table_name} (status, created_at);
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()
            if self._conn is None:
                conn.close()
            logger.info(f"Schema initialized for table {self.table_name}")
        except Exception as e:
            logger.warning(f"Failed to verify/create schema for {self.table_name}: {e}")

    def publish(self, job_ref: JobRef) -> None:
        """Enqueues a job into the outbox_jobs table."""
        payload_json = job_ref.model_dump_json()
        query = f"""
        INSERT INTO {self.table_name} (job_id, application_id, payload, status, retry_count, created_at)
        VALUES (%s, %s, %s, 'PENDING', %s, clock_timestamp())
        ON CONFLICT (job_id) DO NOTHING;
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (job_ref.job_id, job_ref.application_id, payload_json, job_ref.attempt_count - 1))
            conn.commit()
            logger.info(f"Published job {job_ref.job_id} into {self.table_name}")
        finally:
            if self._conn is None:
                conn.close()

    def receive(self, max_n: int = 1, visibility_seconds: int = 30) -> List[Delivery]:
        """
        Atomically claims up to max_n available jobs using FOR UPDATE SKIP LOCKED.
        Updates status to PROCESSING and sets locked_until for lease management.
        """
        query = f"""
        WITH claimed AS (
            SELECT id, job_id, payload
            FROM {self.table_name}
            WHERE status IN ('PENDING', 'DISPATCHED')
              AND (locked_until IS NULL OR locked_until < clock_timestamp())
            ORDER BY created_at ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        UPDATE {self.table_name} t
        SET status = 'PROCESSING',
            locked_until = clock_timestamp() + (%s || ' seconds')::interval,
            dispatched_at = COALESCE(t.dispatched_at, clock_timestamp())
        FROM claimed
        WHERE t.id = claimed.id
        RETURNING t.job_id, t.payload;
        """
        conn = self._get_connection()
        deliveries: List[Delivery] = []
        try:
            with conn.cursor() as cur:
                cur.execute(query, (max_n, str(visibility_seconds)))
                rows = cur.fetchall()
            conn.commit()

            for row in rows:
                job_id = row[0]
                payload_raw = row[1]
                payload_dict = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                job_ref = JobRef.model_validate(payload_dict)
                deliveries.append(Delivery(lease_handle=job_id, job_ref=job_ref))

            return deliveries
        except Exception as e:
            logger.error(f"Error receiving jobs from {self.table_name}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return []
        finally:
            if self._conn is None:
                conn.close()

    def extend_lease(self, handle: str, seconds: int = 30) -> None:
        """Extends locked_until for the given job_id lease handle."""
        query = f"""
        UPDATE {self.table_name}
        SET locked_until = clock_timestamp() + (%s || ' seconds')::interval
        WHERE job_id = %s;
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (str(seconds), handle))
            conn.commit()
            logger.debug(f"Extended lease for {handle} by {seconds}s")
        finally:
            if self._conn is None:
                conn.close()

    def ack(self, handle: str) -> None:
        """Marks the job as COMPLETED and clears the lock."""
        query = f"""
        UPDATE {self.table_name}
        SET status = 'COMPLETED',
            locked_until = NULL,
            completed_at = clock_timestamp()
        WHERE job_id = %s;
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (handle,))
            conn.commit()
            logger.info(f"Acknowledged job {handle} as COMPLETED")
        finally:
            if self._conn is None:
                conn.close()

    def fail(self, handle: str, retryable: bool) -> None:
        """
        Handles job failure:
        - If retryable: resets status to PENDING and increments retry_count for redelivery.
        - If not retryable: marks status as FAILED (DLQ routing).
        """
        target_status = "PENDING" if retryable else "FAILED"
        query = f"""
        UPDATE {self.table_name}
        SET status = %s,
            retry_count = retry_count + 1,
            locked_until = NULL
        WHERE job_id = %s;
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (target_status, handle))
            conn.commit()
            logger.warning(f"Marked job {handle} as {target_status} (retryable={retryable})")
        finally:
            if self._conn is None:
                conn.close()


# Alias for backward compatibility
PostgresQueueAdapter = PostgresQueue


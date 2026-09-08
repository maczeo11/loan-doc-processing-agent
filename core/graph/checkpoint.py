"""
Durable Checkpoint Saver for LangGraph StateGraph persistence.
Owned by Member 2 (Bhanu Teja).

Backs LangGraph graph state into a persistent SQLite datastore so that
interrupted state (such as the human-in-the-loop READY_FOR_REVIEW checkpoint)
survives process restarts, container redeploys, and can be cleanly resumed
by worker consumers or FastAPI HTTP endpoints.
"""

import os
import sqlite3
from typing import Any, Sequence, Optional, Dict
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    ChannelVersions,
    get_checkpoint_id,
    get_checkpoint_metadata,
)
from langchain_core.runnables import RunnableConfig


class SqliteSaver(BaseCheckpointSaver):
    """
    Durable checkpointer that stores graph snapshots, versions, and channel blobs
    in a lightweight SQLite database without external dependencies.
    """

    def __init__(self, db_path: str = "data/storage/checkpoints.sqlite3"):
        super().__init__()
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    checkpoint_id TEXT,
                    parent_checkpoint_id TEXT,
                    checkpoint_type TEXT,
                    checkpoint_bytes BLOB,
                    metadata_type TEXT,
                    metadata_bytes BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_blobs (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    channel TEXT,
                    version TEXT,
                    type TEXT,
                    blob BLOB,
                    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_writes (
                    thread_id TEXT,
                    checkpoint_ns TEXT,
                    checkpoint_id TEXT,
                    task_id TEXT,
                    idx INT,
                    channel TEXT,
                    type TEXT,
                    blob BLOB,
                    task_path TEXT,
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
            """)
            conn.commit()

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if checkpoint_id:
                cursor.execute(
                    "SELECT checkpoint_id, parent_checkpoint_id, checkpoint_type, checkpoint_bytes, metadata_type, metadata_bytes "
                    "FROM checkpoints WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?",
                    (thread_id, checkpoint_ns, checkpoint_id),
                )
            else:
                cursor.execute(
                    "SELECT checkpoint_id, parent_checkpoint_id, checkpoint_type, checkpoint_bytes, metadata_type, metadata_bytes "
                    "FROM checkpoints WHERE thread_id = ? AND checkpoint_ns = ? ORDER BY checkpoint_id DESC LIMIT 1",
                    (thread_id, checkpoint_ns),
                )
            row = cursor.fetchone()
            if not row:
                return None

            cid, parent_cid, c_type, c_bytes, m_type, m_bytes = row
            checkpoint_ = self.serde.loads_typed((c_type, c_bytes))
            metadata = self.serde.loads_typed((m_type, m_bytes))

            cursor.execute(
                "SELECT channel, version, type, blob FROM checkpoint_blobs WHERE thread_id = ? AND checkpoint_ns = ?",
                (thread_id, checkpoint_ns),
            )
            blob_rows = cursor.fetchall()
            blob_map = {(r[0], str(r[1])): (r[2], r[3]) for r in blob_rows}

            channel_values: Dict[str, Any] = {}
            for k, ver in checkpoint_.get("channel_versions", {}).items():
                s_ver = str(ver)
                if (k, s_ver) in blob_map:
                    b_type, b_data = blob_map[(k, s_ver)]
                    if b_type != "empty":
                        channel_values[k] = self.serde.loads_typed((b_type, b_data))

            cursor.execute(
                "SELECT task_id, channel, type, blob, task_path FROM checkpoint_writes "
                "WHERE thread_id = ? AND checkpoint_ns = ? AND checkpoint_id = ?",
                (thread_id, checkpoint_ns, cid),
            )
            writes = [
                (r[0], r[1], self.serde.loads_typed((r[2], r[3])))
                for r in cursor.fetchall()
            ]

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": cid,
                    }
                },
                checkpoint={**checkpoint_, "channel_values": channel_values},
                metadata=metadata,
                pending_writes=writes,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_cid,
                        }
                    }
                    if parent_cid
                    else None
                ),
            )

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        c = checkpoint.copy()
        values = c.pop("channel_values")
        parent_cid = config["configurable"].get("checkpoint_id")

        c_type, c_bytes = self.serde.dumps_typed(c)
        m_type, m_bytes = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))

        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (thread_id, checkpoint_ns, checkpoint["id"], parent_cid, c_type, c_bytes, m_type, m_bytes),
            )
            for k, v in new_versions.items():
                b_type, b_bytes = self.serde.dumps_typed(values[k]) if k in values else ("empty", b"")
                conn.execute(
                    "INSERT OR REPLACE INTO checkpoint_blobs VALUES (?, ?, ?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, k, str(v), b_type, b_bytes),
                )
            conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id: str = config["configurable"]["checkpoint_id"]

        with self._get_connection() as conn:
            for idx, (channel, val) in enumerate(writes):
                v_type, v_bytes = self.serde.dumps_typed(val)
                conn.execute(
                    "INSERT OR REPLACE INTO checkpoint_writes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel, v_type, v_bytes, task_path),
                )
            conn.commit()

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        return self.get_tuple(config)

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

    def list(self, config: Optional[RunnableConfig] = None, **kwargs):
        return iter([])

    async def alist(self, config: Optional[RunnableConfig] = None, **kwargs):
        for item in self.list(config, **kwargs):
            yield item

"""Initial PostgreSQL schema for FinScan AI foundation.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-09-08 20:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

VALID_STATUSES = "('UPLOADED', 'QUEUED', 'PROCESSING', 'READY_FOR_REVIEW', 'NEEDS_INFORMATION', 'REVIEWED', 'FAILED', 'CANCELLED')"
VALID_OUTBOX_STATUSES = "('PENDING', 'PUBLISHED', 'FAILED')"


def upgrade() -> None:
    # 1. applications table
    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("applicant_name", sa.String(length=255), nullable=False),
        sa.Column("loan_amount", sa.Float(), nullable=False),
        sa.Column("loan_purpose", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), nullable=True),
        sa.Column("state_json", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"status IN {VALID_STATUSES}", name="ck_application_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_status", "applications", ["status"], unique=False)

    # 2. documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_uri", sa.String(length=512), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_application_id", "documents", ["application_id"], unique=False)

    # 3. jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_application_id", "jobs", ["application_id"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)

    # 4. outbox_events table
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"status IN {VALID_OUTBOX_STATUSES}", name="ck_outbox_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"], unique=False)
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"], unique=False)
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"], unique=False)
    op.create_index("ix_outbox_events_status_created", "outbox_events", ["status", "created_at"], unique=False)

    # 5. audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=64), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("corrections", json_type, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_application_id", "audit_events", ["application_id"], unique=False)
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"], unique=False)

    # 6. spend_ledger table
    op.create_table(
        "spend_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_or_app_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("cost_units", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spend_ledger_user_or_app_id", "spend_ledger", ["user_or_app_id"], unique=False)
    op.create_index("ix_spend_ledger_timestamp", "spend_ledger", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_table("spend_ledger")
    op.drop_table("audit_events")
    op.drop_table("outbox_events")
    op.drop_table("jobs")
    op.drop_table("documents")
    op.drop_table("applications")

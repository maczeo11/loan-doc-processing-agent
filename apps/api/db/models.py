"""
Declarative SQLAlchemy ORM models for FinScan AI PostgreSQL schema.

Canonical tables:
- applications: Durable state container matching LoanApplicationState
- documents: Uploaded dossier documents with hash and storage URI
- jobs: Worker processing queue tracking and leasing
- outbox_events: Transactional outbox events for atomic publication with last_error tracking
- audit_events: Append-only ledger of status transitions and reviewer actions
- spend_ledger: Resource and cost accounting
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy import (
    String,
    Float,
    Integer,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Confirmed canonical application statuses from core/contracts/state.py
VALID_APPLICATION_STATUSES = (
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "READY_FOR_REVIEW",
    "NEEDS_INFORMATION",
    "REVIEWED",
    "FAILED",
    "CANCELLED",
)

STATUS_CHECK_EXPR = "status IN (" + ", ".join(f"'{s}'" for s in VALID_APPLICATION_STATUSES) + ")"

VALID_OUTBOX_STATUSES = ("PENDING", "PUBLISHED", "FAILED")
OUTBOX_CHECK_EXPR = "status IN (" + ", ".join(f"'{s}'" for s in VALID_OUTBOX_STATUSES) + ")"


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class for all FinScan AI database models."""
    pass


class ApplicationModel(Base):
    """
    Loan application container.
    Authoritative persistence of the application dossier and current state.
    """
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="e.g. APP-25195")
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    loan_amount: Mapped[float] = mapped_column(Float, nullable=False)
    loan_purpose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UPLOADED",
        index=True,
    )
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    state_json: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        comment="Authoritative LoanApplicationState payload",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    __table_args__ = (
        CheckConstraint(STATUS_CHECK_EXPR, name="ck_application_status"),
    )

    # Relationships with selectin loading for native async ORM support
    documents: Mapped[List["DocumentModel"]] = relationship(
        "DocumentModel",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    jobs: Mapped[List["JobModel"]] = relationship(
        "JobModel",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    audit_events: Mapped[List["AuditEventModel"]] = relationship(
        "AuditEventModel",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class DocumentModel(Base):
    """
    Registered dossier document metadata.
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="e.g. DOC-12345")
    application_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    doc_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relationship
    application: Mapped["ApplicationModel"] = relationship(
        "ApplicationModel",
        back_populates="documents",
    )


class JobModel(Base):
    """
    Asynchronous pipeline processing jobs.
    """
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="e.g. JOB-12345")
    application_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lease_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationship
    application: Mapped["ApplicationModel"] = relationship(
        "ApplicationModel",
        back_populates="jobs",
    )


class OutboxEventModel(Base):
    """
    Transactional outbox events for atomic commit with business entities.
    Pending events are polled and published to the queue by the outbox dispatcher.
    """
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(OUTBOX_CHECK_EXPR, name="ck_outbox_status"),
        Index("ix_outbox_events_status_created", "status", "created_at"),
    )


class AuditEventModel(Base):
    """
    Append-only audit trail for application lifecycle transitions and reviewer decisions.
    """
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    application_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrections: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    # Relationship
    application: Mapped["ApplicationModel"] = relationship(
        "ApplicationModel",
        back_populates="audit_events",
    )


class SpendLedgerModel(Base):
    """
    Append-only ledger for tracking operational spending and quota usage.
    """
    __tablename__ = "spend_ledger"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_or_app_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_units: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

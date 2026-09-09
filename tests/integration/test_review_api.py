"""
Integration tests for human review and sign-off API endpoint (POST /applications/{id}/review).
Owned by Member 6 (Balaji) & Member 2 (Bhanu Teja).

Validates:
1. Underwriter sign-off (APPROVED -> REVIEWED)
2. Underwriter rejection (REJECTED -> REVIEWED)
3. Underwriter info request (NEEDS_INFO -> NEEDS_INFORMATION)
4. Conflict 409 when application is not in READY_FOR_REVIEW state
5. Not Found 404 for unknown application ID
6. Immutable AuditEventModel persistence in audit_events table
7. Resumption with active SqliteSaver checkpointer
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.db.models import Base, ApplicationModel, AuditEventModel, utc_now
from apps.api.db.session import get_db
from core.contracts.state import LoanApplicationState
from core.graph.checkpoint import SqliteSaver
from core.graph.workflow import build_application_graph
from apps.api.routes.review import _serialize_state_for_db


@pytest_asyncio.fixture
async def review_test_env():
    """
    Sets up an isolated test database and an AsyncClient with get_db override.
    """
    db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield session_factory, client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _build_ready_for_review_state(app_id: str) -> dict:
    now_iso = utc_now().isoformat()
    raw_state: LoanApplicationState = {
        "application_id": app_id,
        "status": "READY_FOR_REVIEW",
        "status_history": [
            {"from_status": "UPLOADED", "to_status": "QUEUED", "timestamp": now_iso, "reason": "Queued"},
            {"from_status": "QUEUED", "to_status": "PROCESSING", "timestamp": now_iso, "reason": "Processing"},
            {"from_status": "PROCESSING", "to_status": "READY_FOR_REVIEW", "timestamp": now_iso, "reason": "Ready"},
        ],
        "document_ids": [f"{app_id}-doc1"],
        "document_manifest": {f"{app_id}-doc1": f"storage/{app_id}/doc1.pdf"},
        "classified_types": {f"{app_id}-doc1": "payslip"},
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": ["credit_policy_v1_p1"],
        "summary_markdown": "### Credit Appraisal Memo\nAll checks passed.",
        "summary_grounded": True,
        "review_paused": True,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }
    return _serialize_state_for_db(raw_state)



@pytest.mark.asyncio
async def test_review_approve_transitions_to_reviewed_and_commits_audit(review_test_env):
    """
    Submitting APPROVED decision transitions application to REVIEWED,
    records reviewer_id, and commits an immutable AuditEventModel row.
    """
    session_factory, client = review_test_env
    app_id = "APP-REV-001"

    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Sunil Gavaskar",
            loan_amount=500000.0,
            loan_purpose="Vehicle Loan",
            status="READY_FOR_REVIEW",
            state_json=_build_ready_for_review_state(app_id),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "APPROVED",
        "reviewer_id": "UW-OFFICER-77",
        "notes": "Verified payroll credits and tax filings.",
        "corrections": [],
    }
    response = await client.post(f"/applications/{app_id}/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["application_id"] == app_id
    assert data["status"] == "REVIEWED"
    assert data["decision"] == "APPROVED"
    assert data["reviewer_id"] == "UW-OFFICER-77"
    assert data["notes"] == "Verified payroll credits and tax filings."

    # Verify ApplicationModel in database
    async with session_factory() as session:
        db_app = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()

        assert db_app.status == "REVIEWED"
        assert db_app.reviewer_id == "UW-OFFICER-77"
        assert db_app.state_json["status"] == "REVIEWED"
        assert db_app.state_json["reviewer_decision"] == "APPROVED"
        assert db_app.state_json["review_paused"] is False

        # Verify AuditEventModel in database
        audit_res = await session.execute(
            select(AuditEventModel).where(AuditEventModel.application_id == app_id)
        )
        audit_events = audit_res.scalars().all()
        assert len(audit_events) == 1
        event = audit_events[0]
        assert event.from_status == "READY_FOR_REVIEW"
        assert event.to_status == "REVIEWED"
        assert event.actor == "UW-OFFICER-77"
        assert event.decision == "APPROVED"
        assert event.notes == "Verified payroll credits and tax filings."


@pytest.mark.asyncio
async def test_review_reject_transitions_to_reviewed(review_test_env):
    """
    Submitting REJECTED decision transitions application to REVIEWED with rejection reason.
    """
    session_factory, client = review_test_env
    app_id = "APP-REV-002"

    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Kapil Dev",
            loan_amount=1500000.0,
            status="READY_FOR_REVIEW",
            state_json=_build_ready_for_review_state(app_id),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "REJECTED",
        "reviewer_id": "UW-SENIOR-12",
        "notes": "Salary credits do not match stated gross income by > 15%.",
        "corrections": [],
    }
    response = await client.post(f"/applications/{app_id}/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REVIEWED"
    assert data["decision"] == "REJECTED"

    async with session_factory() as session:
        db_app = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert db_app.status == "REVIEWED"
        assert db_app.reviewer_id == "UW-SENIOR-12"


@pytest.mark.asyncio
async def test_review_needs_info_transitions_to_needs_information(review_test_env):
    """
    Submitting NEEDS_INFO transitions application to NEEDS_INFORMATION.
    """
    session_factory, client = review_test_env
    app_id = "APP-REV-003"

    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Rahul Dravid",
            loan_amount=750000.0,
            status="READY_FOR_REVIEW",
            state_json=_build_ready_for_review_state(app_id),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "NEEDS_INFO",
        "reviewer_id": "UW-OFFICER-03",
        "notes": "Bank statement page 3 is blurry. Please provide legible scan.",
        "corrections": [],
    }
    response = await client.post(f"/applications/{app_id}/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NEEDS_INFORMATION"
    assert data["decision"] == "NEEDS_INFO"

    async with session_factory() as session:
        db_app = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert db_app.status == "NEEDS_INFORMATION"
        assert db_app.reviewer_id == "UW-OFFICER-03"


@pytest.mark.asyncio
async def test_review_nonexistent_application_returns_404(review_test_env):
    """
    Reviewing non-existent application returns 404 Not Found.
    """
    _, client = review_test_env
    payload = {
        "decision": "APPROVED",
        "reviewer_id": "UW-01",
        "notes": "LGTM",
    }
    response = await client.post("/applications/APP-GHOST-999/review", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_review_unready_application_returns_409_conflict(review_test_env):
    """
    Attempting to submit review for an application not in READY_FOR_REVIEW returns 409 Conflict.
    """
    session_factory, client = review_test_env
    app_id = "APP-REV-CONFLICT"

    # Seed application in UPLOADED state
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="Sachin Tendulkar",
            loan_amount=2000000.0,
            status="UPLOADED",
            state_json={"application_id": app_id, "status": "UPLOADED"},
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    payload = {
        "decision": "APPROVED",
        "reviewer_id": "UW-01",
        "notes": "Premature approval attempt",
    }
    response = await client.post(f"/applications/{app_id}/review", json=payload)
    assert response.status_code == 409
    assert "cannot be reviewed" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_review_resumes_sqlite_checkpointer(review_test_env, tmp_path, monkeypatch):
    """
    Verifies that when an active SqliteSaver checkpointer contains an interrupted
    READY_FOR_REVIEW state, POST /review resumes the graph checkpointer properly.
    """
    session_factory, client = review_test_env
    app_id = "APP-REV-CHECKPOINT"

    # Setup isolated SQLite checkpointer
    ckpt_path = str(tmp_path / "review_checkpoints.sqlite3")
    checkpointer = SqliteSaver(db_path=ckpt_path)

    # Monkeypatch get_default_checkpointer in core.graph.workflow
    import core.graph.workflow as wf
    monkeypatch.setattr(wf, "get_default_checkpointer", lambda *args, **kwargs: checkpointer)

    # Pre-populate stategraph checkpoint paused at READY_FOR_REVIEW
    graph = build_application_graph(checkpointer=checkpointer, enable_interrupt=True)
    initial_state = _build_ready_for_review_state(app_id)
    initial_state["status"] = "QUEUED"
    config = {"configurable": {"thread_id": app_id}}

    paused_state = graph.invoke(initial_state, config=config)
    assert paused_state["status"] == "READY_FOR_REVIEW"

    # Seed DB ApplicationModel
    async with session_factory() as session:
        app_model = ApplicationModel(
            id=app_id,
            applicant_name="VVS Laxman",
            loan_amount=900000.0,
            status="READY_FOR_REVIEW",
            state_json=_serialize_state_for_db(paused_state),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(app_model)
        await session.commit()

    # Submit review via API
    payload = {
        "decision": "APPROVED",
        "reviewer_id": "UW-CHIEF-01",
        "notes": "Verified through checkpointer resumption.",
    }
    response = await client.post(f"/applications/{app_id}/review", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REVIEWED"

    # Check DB
    async with session_factory() as session:
        db_app = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert db_app.status == "REVIEWED"
        assert db_app.reviewer_id == "UW-CHIEF-01"
        assert db_app.state_json["status"] == "REVIEWED"
        assert db_app.state_json["reviewer_decision"] == "APPROVED"

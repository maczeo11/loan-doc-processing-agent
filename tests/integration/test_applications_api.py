"""
Integration tests for Applications API endpoints (POST /applications, GET /applications/{id}).
"""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.db.models import Base
from apps.api.db.session import get_db


@pytest_asyncio.fixture
async def test_db_session_and_client():
    """
    Sets up an isolated test database (PostgreSQL if TEST_DATABASE_URL set, else SQLite)
    and an AsyncClient wired with get_db override.
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


@pytest.mark.asyncio
async def test_create_application_persists_uploaded_and_state_json(test_db_session_and_client):
    """Verifies POST /applications creates application with UPLOADED status and minimal state."""
    _, client = test_db_session_and_client

    payload = {
        "applicant_name": "Vikram Seth",
        "loan_amount": 1200000.0,
        "loan_purpose": "Home Purchase",
    }
    response = await client.post("/applications", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "UPLOADED"
    app_id = data["application_id"]
    assert app_id.startswith("APP-")

    # Read back through GET /applications/{id}
    get_res = await client.get(f"/applications/{app_id}")
    assert get_res.status_code == 200
    state = get_res.json()
    assert state["application_id"] == app_id
    assert state["status"] == "UPLOADED"
    assert len(state["status_history"]) == 1
    assert state["status_history"][0]["from_status"] == "UPLOADED"
    assert state["status_history"][0]["to_status"] == "UPLOADED"
    assert state["document_ids"] == []
    assert state["findings"] == []
    assert state["applicant"] is None
    assert state["payslip"] is None


@pytest.mark.asyncio
async def test_get_unknown_application_returns_404(test_db_session_and_client):
    """Verifies GET /applications/{id} returns 404 for non-existent application."""
    _, client = test_db_session_and_client
    response = await client.get("/applications/APP-NONEXISTENT")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

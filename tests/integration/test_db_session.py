"""
Integration tests for database session lifecycle, transactions, rollback, and Alembic migrations.
"""

import os
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from alembic.config import Config

from apps.api.db.session import (
    get_async_engine,
    get_session_factory,
    get_db,
)
from apps.api.db.models import Base, ApplicationModel


@pytest_asyncio.fixture
async def isolated_engine_and_factory(tmp_path):
    """
    Creates an isolated async engine and session factory.
    Uses TEST_DATABASE_URL if provided, else an isolated SQLite database file.
    """
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        sqlite_file = tmp_path / "finscan_test.db"
        db_url = f"sqlite+aiosqlite:///{sqlite_file}"

    test_engine = get_async_engine(database_url=db_url)
    session_factory = get_session_factory(test_engine)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine, session_factory

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_session_commit_persists_data(isolated_engine_and_factory):
    """Verifies that an async session commit persists data cleanly."""
    _, session_factory = isolated_engine_and_factory

    async with session_factory() as session:
        app = ApplicationModel(
            id="APP-COMMIT-01",
            applicant_name="Rohan Varma",
            loan_amount=750000.0,
            status="UPLOADED",
            state_json={},
        )
        session.add(app)
        await session.commit()

    # Read from separate session to confirm durability
    async with session_factory() as read_session:
        result = await read_session.execute(
            select(ApplicationModel).where(ApplicationModel.id == "APP-COMMIT-01")
        )
        app_read = result.scalar_one_or_none()
        assert app_read is not None
        assert app_read.applicant_name == "Rohan Varma"


@pytest.mark.asyncio
async def test_failed_transaction_leaves_no_partial_data(isolated_engine_and_factory):
    """
    Verifies that when a transaction fails mid-way, all changes are rolled back
    and no partial data remains in the database.
    """
    _, session_factory = isolated_engine_and_factory

    with pytest.raises(RuntimeError):
        async with session_factory() as session:
            # 1. Add valid application
            app = ApplicationModel(
                id="APP-ATOMIC-FAIL",
                applicant_name="Atomic Tester",
                loan_amount=300000.0,
                status="UPLOADED",
                state_json={},
            )
            session.add(app)
            await session.flush()  # Flushed to buffer but not committed

            # 2. Simulate failure before commit
            raise RuntimeError("Simulated transaction failure")

    # Read from separate session: Verify application was NOT persisted
    async with session_factory() as verify_session:
        result = await verify_session.execute(
            select(ApplicationModel).where(ApplicationModel.id == "APP-ATOMIC-FAIL")
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_get_db_dependency_lifecycle(isolated_engine_and_factory, monkeypatch):
    """Verifies FastAPI get_db dependency yields, auto-commits or rolls back, and closes."""
    _, session_factory = isolated_engine_and_factory

    # Monkeypatch session factory for testing dependency
    import apps.api.db.session as session_module
    monkeypatch.setattr(session_module, "async_session_factory", session_factory)

    # 1. Normal execution
    db_gen = get_db()
    session = await anext(db_gen)
    assert isinstance(session, AsyncSession)
    assert session.is_active

    app = ApplicationModel(
        id="APP-DEP-01",
        applicant_name="Dependency Tester",
        loan_amount=100000.0,
        status="UPLOADED",
        state_json={},
    )
    session.add(app)
    await session.commit()

    # Finish generator
    with pytest.raises(StopAsyncIteration):
        await anext(db_gen)

    # 2. Exception propagation triggers rollback
    db_gen_err = get_db()
    session_err = await anext(db_gen_err)
    session_err.add(
        ApplicationModel(
            id="APP-DEP-ERR",
            applicant_name="Rollback Tester",
            loan_amount=200000.0,
            status="UPLOADED",
            state_json={},
        )
    )
    await session_err.flush()

    with pytest.raises(ValueError):
        await db_gen_err.athrow(ValueError("Simulated route error"))

    # Confirm rollback
    async with session_factory() as check_session:
        res = await check_session.execute(
            select(ApplicationModel).where(ApplicationModel.id == "APP-DEP-ERR")
        )
        assert res.scalar_one_or_none() is None


def test_alembic_upgrade_and_downgrade_migration(tmp_path):
    """
    Verifies that Alembic migration 001_initial_schema upgrades a clean database
    and creates all expected tables, then downgrades cleanly.
    """
    test_sqlite_file = tmp_path / "alembic_test.db"
    test_db_url = f"sqlite:///{test_sqlite_file.as_posix()}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

    # Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Verify tables were created
    from sqlalchemy import create_engine, inspect
    sync_engine = create_engine(test_db_url)
    inspector = inspect(sync_engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "alembic_version",
        "applications",
        "documents",
        "jobs",
        "outbox_events",
        "audit_events",
        "spend_ledger",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"

    # Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(sync_engine)
    remaining_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert len(remaining_tables) == 0, f"Tables remaining after downgrade: {remaining_tables}"

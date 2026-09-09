"""
Integration tests for document upload API:
- POST /applications/{id}/documents
- Canonical build_storage_key usage (dossiers/{app_id}/{doc_id}_{filename})
- SHA-256 calculation and exact byte count
- Real adapter and test double storage integration
- Safe cleanup / orphaned object logging on DB failure
- Strict failure isolation (no partial DB or state mutations)
"""

import io
import os
import hashlib
import logging
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.main import app
from apps.api.config import settings
from apps.api.db.models import Base, ApplicationModel, DocumentModel
from apps.api.db.session import get_db
from apps.api.storage import get_storage
import apps.api.routes.documents as doc_route_module
from adapters.storage.base import StoragePort
from adapters.storage.local_fs import LocalFileSystemStorage


class MockStorageWithDelete(StoragePort):
    """Test double implementing StoragePort plus optional delete capability."""

    def __init__(self, should_fail: bool = False):
        self.stored = {}
        self.deleted = []
        self.should_fail = should_fail

    def put(self, key: str, data) -> str:
        if self.should_fail:
            raise RuntimeError("Simulated storage error during put()")
        content = data.read()
        self.stored[key] = content
        return f"file://mock_storage/{key}"

    def get(self, key: str) -> bytes:
        return self.stored.get(key, b"")

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/mock_storage/{key}"

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.stored.pop(key, None)


class StrictStorageWithoutDelete(StoragePort):
    """Test double strictly adhering to frozen StoragePort protocol without delete method."""

    def __init__(self):
        self.stored = {}

    def put(self, key: str, data) -> str:
        content = data.read()
        self.stored[key] = content
        return f"file://strict_storage/{key}"

    def get(self, key: str) -> bytes:
        return self.stored.get(key, b"")

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/strict_storage/{key}"


@pytest_asyncio.fixture
async def test_env():
    """Sets up an isolated database, mock storage, and AsyncClient."""
    # Ensure document logger is enabled even if Alembic migrations ran previously
    logging.getLogger("finscan.documents").disabled = False

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

    mock_storage = MockStorageWithDelete()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = lambda: mock_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield session_factory, client, mock_storage

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_document_success_persists_metadata_and_state(test_env):
    """
    Verifies successful document upload:
    - Calculates real SHA-256 and byte size.
    - Stores file in StoragePort using canonical flattened key.
    - Persists DocumentModel in PostgreSQL.
    - Updates application document_ids, document_manifest, and classified_types.
    """
    session_factory, client, mock_storage = test_env

    # 1. Create application
    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Rohan Mehra", "loan_amount": 600000.0},
    )
    app_id = create_res.json()["application_id"]

    # 2. Upload valid PDF document
    pdf_content = b"%PDF-1.5 \n%Binary simulated pdf payload with text data\n%%EOF"
    expected_sha256 = hashlib.sha256(pdf_content).hexdigest()
    expected_size = len(pdf_content)

    files = {
        "file": ("payslip_may.pdf", io.BytesIO(pdf_content), "application/pdf")
    }
    data = {"doc_type_hint": "payslip"}

    upload_res = await client.post(
        f"/applications/{app_id}/documents",
        files=files,
        data=data,
    )
    assert upload_res.status_code == 201
    resp_data = upload_res.json()

    doc_id = resp_data["document_id"]
    assert doc_id.startswith("DOC-")
    assert resp_data["application_id"] == app_id
    assert resp_data["filename"] == "payslip_may.pdf"
    assert resp_data["sha256"] == expected_sha256
    assert resp_data["size_bytes"] == expected_size

    # Verify key in mock storage conforms to dossiers/{app_id}/{doc_id}_{filename}
    expected_key = f"dossiers/{app_id}/{doc_id}_payslip_may.pdf"
    assert expected_key in mock_storage.stored

    # 3. Verify PostgreSQL DocumentModel and application state_json
    async with session_factory() as session:
        doc_record = (await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc_id)
        )).scalar_one()

        assert doc_record.filename == "payslip_may.pdf"
        assert doc_record.sha256 == expected_sha256
        assert doc_record.size_bytes == expected_size
        assert doc_record.doc_type == "payslip"
        assert doc_record.storage_uri == f"file://mock_storage/{expected_key}"

        app_record = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()

        state = app_record.state_json
        assert doc_id in state["document_ids"]
        assert state["document_manifest"][doc_id] == doc_record.storage_uri
        assert state["classified_types"][doc_id] == "payslip"


@pytest.mark.asyncio
async def test_upload_with_real_local_filesystem_adapter(test_env):
    """
    Verifies upload works end-to-end using the existing LocalFileSystemStorage adapter
    and canonical build_storage_key format: dossiers/{app_id}/{doc_id}_{filename}.
    """
    session_factory, client, _ = test_env

    # Configure storage to use actual LocalFileSystemStorage adapter
    local_adapter = LocalFileSystemStorage(base_dir=settings.STORAGE_BASE_DIR)
    app.dependency_overrides[get_storage] = lambda: local_adapter

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Adapter Verification", "loan_amount": 250000.0},
    )
    app_id = create_res.json()["application_id"]

    pdf_content = b"%PDF-1.4 \nReal adapter payload\n%%EOF"
    files = {"file": ("bank_stmt.pdf", io.BytesIO(pdf_content), "application/pdf")}

    upload_res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert upload_res.status_code == 201
    data = upload_res.json()
    doc_id = data["document_id"]

    # Verify storage URI matches canonical build_storage_key convention
    async with session_factory() as session:
        doc = (await session.execute(
            select(DocumentModel).where(DocumentModel.id == doc_id)
        )).scalar_one()
        from pathlib import Path
        expected_path = Path(settings.STORAGE_BASE_DIR).resolve() / "dossiers" / app_id / f"{doc_id}_bank_stmt.pdf"
        expected_uri = f"file://{expected_path.as_posix()}"
        assert doc.storage_uri == expected_uri


@pytest.mark.asyncio
async def test_upload_same_filename_twice_generates_distinct_storage_keys(test_env):
    """
    Verifies uploading the same filename twice to an application produces
    two distinct document IDs and distinct flattened storage keys.
    """
    session_factory, client, mock_storage = test_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Multi Upload User", "loan_amount": 400000.0},
    )
    app_id = create_res.json()["application_id"]

    pdf_1 = b"%PDF-1.4 Version 1 content"
    pdf_2 = b"%PDF-1.4 Version 2 content"

    res1 = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("salary_slip.pdf", io.BytesIO(pdf_1), "application/pdf")},
    )
    assert res1.status_code == 201
    doc_id_1 = res1.json()["document_id"]

    res2 = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("salary_slip.pdf", io.BytesIO(pdf_2), "application/pdf")},
    )
    assert res2.status_code == 201
    doc_id_2 = res2.json()["document_id"]

    assert doc_id_1 != doc_id_2

    key1 = f"dossiers/{app_id}/{doc_id_1}_salary_slip.pdf"
    key2 = f"dossiers/{app_id}/{doc_id_2}_salary_slip.pdf"
    assert key1 != key2
    assert key1 in mock_storage.stored
    assert key2 in mock_storage.stored

    # Verify application manifest contains both distinct URIs
    async with session_factory() as session:
        app_record = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        manifest = app_record.state_json["document_manifest"]
        assert manifest[doc_id_1] == f"file://mock_storage/{key1}"
        assert manifest[doc_id_2] == f"file://mock_storage/{key2}"


@pytest.mark.asyncio
async def test_route_uses_build_storage_key_canonical_function(test_env):
    """
    Verifies the upload route explicitly calls build_storage_key rather than
    an ad-hoc local string formatting.
    """
    _, client, _ = test_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Spy Caller", "loan_amount": 150000.0},
    )
    app_id = create_res.json()["application_id"]

    calls = []
    real_build_key = doc_route_module.build_storage_key

    def spy_build_storage_key(application_id, document_id, filename, **kwargs):
        calls.append((application_id, document_id, filename))
        return real_build_key(application_id=application_id, document_id=document_id, filename=filename)

    with patch.object(doc_route_module, "build_storage_key", side_effect=spy_build_storage_key):
        files = {"file": ("id_proof.pdf", io.BytesIO(b"%PDF-1.4 id proof bytes"), "application/pdf")}
        res = await client.post(f"/applications/{app_id}/documents", files=files)
        assert res.status_code == 201

    assert len(calls) == 1
    assert calls[0][0] == app_id
    assert calls[0][1].startswith("DOC-")
    assert calls[0][2] == "id_proof.pdf"


@pytest.mark.asyncio
async def test_upload_to_unknown_application_returns_404(test_env):
    """Verifies upload returns 404 when target application does not exist."""
    _, client, _ = test_env
    files = {
        "file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 sample content"), "application/pdf")
    }
    res = await client.post("/applications/APP-NONEXISTENT/documents", files=files)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_upload_invalid_signature_rejected_with_400(test_env):
    """Verifies file with fake PDF extension but non-PDF content is rejected."""
    _, client, _ = test_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Security Tester", "loan_amount": 100000.0},
    )
    app_id = create_res.json()["application_id"]

    files = {
        "file": ("fake.pdf", io.BytesIO(b"This is not a PDF file header"), "application/pdf")
    }
    res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert res.status_code == 400
    assert "magic bytes" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_path_traversal_filename_rejected(test_env):
    """Verifies filename with directory traversal is rejected."""
    _, client, _ = test_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Traversal Tester", "loan_amount": 100000.0},
    )
    app_id = create_res.json()["application_id"]

    files = {
        "file": ("../../etc/passwd.pdf", io.BytesIO(b"%PDF-1.4 header"), "application/pdf")
    }
    res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert res.status_code == 400
    assert "path traversal" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_storage_failure_leaves_no_database_record(test_env):
    """
    Verifies that when StoragePort.put() fails, zero document rows are created
    and application state is completely unchanged.
    """
    session_factory, client, mock_storage = test_env
    mock_storage.should_fail = True

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Storage Fail Tester", "loan_amount": 200000.0},
    )
    app_id = create_res.json()["application_id"]

    files = {
        "file": ("payslip.pdf", io.BytesIO(b"%PDF-1.4 test payload"), "application/pdf")
    }
    res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert res.status_code == 500

    async with session_factory() as session:
        docs = (await session.execute(
            select(DocumentModel).where(DocumentModel.application_id == app_id)
        )).scalars().all()
        assert len(docs) == 0

        app_record = (await session.execute(
            select(ApplicationModel).where(ApplicationModel.id == app_id)
        )).scalar_one()
        assert app_record.state_json["document_ids"] == []
        assert app_record.state_json["document_manifest"] == {}


@pytest.mark.asyncio
async def test_database_failure_triggers_storage_cleanup_when_available(test_env, monkeypatch):
    """
    Verifies that if storage succeeds but database commit fails,
    safe cleanup is invoked on storage if the adapter supports delete().
    """
    session_factory, client, mock_storage = test_env

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Cleanup Tester", "loan_amount": 300000.0},
    )
    app_id = create_res.json()["application_id"]

    async def failing_commit():
        raise RuntimeError("Simulated DB connection drop during document commit")

    files = {
        "file": ("payslip.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")
    }

    orig_commit = AsyncSession.commit
    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    res = await client.post(f"/applications/{app_id}/documents", files=files)
    assert res.status_code == 500
    assert "failed to persist document metadata" in res.json()["detail"].lower()

    # Verify storage cleanup was attempted and object deleted
    assert len(mock_storage.deleted) == 1
    assert mock_storage.deleted[0].startswith(f"dossiers/{app_id}/")

    monkeypatch.setattr(AsyncSession, "commit", orig_commit)

    async with session_factory() as session:
        docs = (await session.execute(
            select(DocumentModel).where(DocumentModel.application_id == app_id)
        )).scalars().all()
        assert len(docs) == 0


@pytest.mark.asyncio
async def test_database_failure_without_delete_capability_logs_orphaned_object(test_env, monkeypatch, caplog):
    """
    Verifies that when StoragePort implementation lacks delete capability (frozen protocol),
    a DB commit failure clearly logs the orphaned object warning and leaves DB untouched.
    """
    session_factory, client, _ = test_env
    strict_storage = StrictStorageWithoutDelete()
    app.dependency_overrides[get_storage] = lambda: strict_storage

    create_res = await client.post(
        "/applications",
        json={"applicant_name": "Strict Storage Tester", "loan_amount": 350000.0},
    )
    app_id = create_res.json()["application_id"]

    async def failing_commit():
        raise RuntimeError("Simulated DB connection drop")

    orig_commit = AsyncSession.commit
    monkeypatch.setattr(AsyncSession, "commit", failing_commit)

    files = {
        "file": ("tax_return.pdf", io.BytesIO(b"%PDF-1.4 content"), "application/pdf")
    }

    logging.getLogger("finscan.documents").disabled = False
    with caplog.at_level(logging.WARNING, logger="finscan.documents"):
        res = await client.post(f"/applications/{app_id}/documents", files=files)
        assert res.status_code == 500

    # Verify orphaned object warning was logged
    warning_records = [r for r in caplog.records if "remains orphaned after db rollback" in r.message.lower()]
    assert len(warning_records) == 1
    assert f"dossiers/{app_id}/" in warning_records[0].message

    monkeypatch.setattr(AsyncSession, "commit", orig_commit)

    async with session_factory() as session:
        docs = (await session.execute(
            select(DocumentModel).where(DocumentModel.application_id == app_id)
        )).scalars().all()
        assert len(docs) == 0

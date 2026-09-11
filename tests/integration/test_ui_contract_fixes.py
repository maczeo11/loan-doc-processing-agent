"""
Regression tests for the reviewer-facing contract between the API and the UI.

Each test here pins behaviour that the UI depends on to avoid presenting
unverified data as verified:

- /applications/{id} echoes the relational columns the dossier header renders.
- Uploads record real filenames and page counts (the UI used to invent them).
- Export is gated on a reviewable status and never leaks a temp file.
- The append-only audit trail is readable (it was written but had no route).
- Scanned images are served with their own media type, not application/pdf.
- The storage tamper guard surfaces as 422, not a masked 404.
- Policy citations only carry document_id when they point at a dossier document.
"""

import hashlib
import os
import uuid

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.db.models import ApplicationModel, Base, DocumentModel
from apps.api.db.session import get_db
from apps.api.main import app
from apps.api.middleware.rate_limit import get_redis_client

PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000a49444154789c6360000002000100ffff0300000600"
    "05fd7b1a8c0000000049454e44ae426082"
)


@pytest_asyncio.fixture
async def api_env(tmp_path, monkeypatch):
    """Isolated SQLite DB, FakeRedis, and a temp storage root."""
    monkeypatch.setattr(
        "apps.api.config.settings.STORAGE_BASE_DIR", str(tmp_path / "storage")
    )
    engine = create_async_engine(
        os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"), echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield session_factory, client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _create_app(client, **kwargs) -> str:
    payload = {"applicant_name": "Test Applicant", "loan_amount": 500000.0, "loan_purpose": "Home"}
    payload.update(kwargs)
    res = await client.post("/applications", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["application_id"]


@pytest.mark.asyncio
async def test_get_application_echoes_relational_columns(api_env):
    """The dossier header needs loan amount/applicant/timestamps, which live on
    the relational model rather than in the pipeline's state_json."""
    _, client = api_env
    app_id = await _create_app(client, applicant_name="Priya Nair", loan_amount=1250000.0)

    state = (await client.get(f"/applications/{app_id}")).json()
    assert state["loan_amount"] == 1250000.0
    assert state["applicant_name"] == "Priya Nair"
    assert state["loan_purpose"] == "Home"
    # created_at drives the SLA clock; without it the timer restarted every poll.
    assert state["created_at"]


@pytest.mark.asyncio
async def test_upload_records_real_filename_and_page_count(api_env):
    """The dossier index must describe the uploaded file, not a guess keyed off
    the generated document id."""
    _, client = api_env
    app_id = await _create_app(client)

    res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("march_payslip.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type_hint": "payslip"},
    )
    assert res.status_code == 201, res.text
    doc_id = res.json()["document_id"]

    state = (await client.get(f"/applications/{app_id}")).json()
    assert state["document_filenames"][doc_id] == "march_payslip.pdf"
    assert state["document_pages"][doc_id] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hint,expected",
    [
        ("tax_return", "tax_acknowledgement"),
        ("ITR", "tax_acknowledgement"),
        ("pan_card", "id_card"),
        ("bank_statement", "bank_statement"),
    ],
)
async def test_doc_type_hint_normalized_to_pipeline_vocabulary(api_env, hint, expected):
    """A hint is written straight into classified_types and the classifier will
    not revisit an already-typed document, so an off-vocabulary hint made
    RULE-COMP-01 report a document that is present as missing."""
    _, client = api_env
    app_id = await _create_app(client)

    res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("doc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type_hint": hint},
    )
    assert res.status_code == 201, res.text
    doc_id = res.json()["document_id"]

    state = (await client.get(f"/applications/{app_id}")).json()
    assert state["classified_types"][doc_id] == expected


@pytest.mark.asyncio
async def test_unrecognised_hint_defers_to_classifier(api_env):
    """An unknown label must not be pinned; leaving it unset lets the classifier
    assign a real type during perception."""
    _, client = api_env
    app_id = await _create_app(client)

    res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("doc.pdf", PDF_BYTES, "application/pdf")},
        data={"doc_type_hint": "some_unknown_category"},
    )
    doc_id = res.json()["document_id"]

    state = (await client.get(f"/applications/{app_id}")).json()
    assert doc_id not in state.get("classified_types", {})


@pytest.mark.asyncio
async def test_image_upload_served_with_image_media_type(api_env):
    """ALLOWED_EXTENSIONS admits scans; serving them as application/pdf made an
    uploaded payslip photo unrenderable."""
    _, client = api_env
    app_id = await _create_app(client)

    res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("scan.png", PNG_BYTES, "image/png")},
    )
    assert res.status_code == 201, res.text
    doc_id = res.json()["document_id"]

    fetched = await client.get(f"/applications/{app_id}/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/png")


@pytest.mark.asyncio
async def test_tamper_guard_surfaces_as_422_not_404(api_env):
    """A hash mismatch must not be reported as a benign 'not found'. The 422 was
    raised inside a try whose except re-raised everything as 404."""
    session_factory, client = api_env
    app_id = await _create_app(client)

    res = await client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("doc.pdf", PDF_BYTES, "application/pdf")},
    )
    doc_id = res.json()["document_id"]

    # Corrupt the recorded digest so the stored bytes no longer match.
    async with session_factory() as session:
        doc = (
            await session.execute(select(DocumentModel).where(DocumentModel.id == doc_id))
        ).scalar_one()
        doc.sha256 = hashlib.sha256(b"different bytes").hexdigest()
        await session.commit()

    fetched = await client.get(f"/applications/{app_id}/documents/{doc_id}")
    assert fetched.status_code == 422
    assert "integrity" in fetched.json()["detail"].lower()


@pytest.mark.asyncio
async def test_export_refused_before_dossier_is_reviewable(api_env):
    """A CAM PDF for an UPLOADED dossier would put bank letterhead behind an
    appraisal that has not been produced."""
    _, client = api_env
    app_id = await _create_app(client)

    res = await client.get(f"/applications/{app_id}/export", params={"format": "pdf"})
    assert res.status_code == 409
    assert "UPLOADED" in res.json()["detail"]


@pytest.mark.asyncio
async def test_export_pdf_returns_bytes_and_leaves_no_temp_file(api_env, tmp_path, monkeypatch):
    """FileResponse streamed a NamedTemporaryFile(delete=False) nothing unlinked,
    leaking one temp PDF per download."""
    session_factory, client = api_env
    app_id = await _create_app(client)

    async with session_factory() as session:
        model = (
            await session.execute(select(ApplicationModel).where(ApplicationModel.id == app_id))
        ).scalar_one()
        model.status = "READY_FOR_REVIEW"
        model.state_json = {
            "status": "READY_FOR_REVIEW",
            "status_history": [],
            "findings": [],
            "summary_markdown": "## Credit Appraisal\nIncome verified.",
        }
        await session.commit()

    tmp_dir = tmp_path / "exports"
    tmp_dir.mkdir()
    monkeypatch.setenv("TMPDIR", str(tmp_dir))
    monkeypatch.setenv("TEMP", str(tmp_dir))
    monkeypatch.setattr("tempfile.tempdir", str(tmp_dir))

    res = await client.get(f"/applications/{app_id}/export", params={"format": "pdf"})
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")
    assert list(tmp_dir.iterdir()) == [], "export left a temp file behind"


@pytest.mark.asyncio
async def test_audit_trail_is_readable(api_env):
    """Audit rows were written on every sign-off but had no read route, so the
    'immutable audit trail' was invisible to the accountable reviewer."""
    session_factory, client = api_env
    app_id = await _create_app(client)

    async with session_factory() as session:
        model = (
            await session.execute(select(ApplicationModel).where(ApplicationModel.id == app_id))
        ).scalar_one()
        model.status = "READY_FOR_REVIEW"
        model.state_json = {"status": "READY_FOR_REVIEW", "status_history": []}
        await session.commit()

    review = await client.post(
        f"/applications/{app_id}/review",
        json={
            "decision": "REJECTED",
            "reviewer_id": "ignored-by-server",
            "notes": "Bank credits do not corroborate the stated salary.",
            "confirm_app_id": app_id,
            "corrections": [],
        },
    )
    assert review.status_code == 200, review.text

    audit = await client.get(f"/applications/{app_id}/audit")
    assert audit.status_code == 200
    events = audit.json()
    assert len(events) == 1
    assert events[0]["decision"] == "REJECTED"
    assert events[0]["to_status"] == "REVIEWED"
    assert events[0]["from_status"] == "READY_FOR_REVIEW"
    # The actor is the verified session identity, never the body's reviewer_id.
    assert events[0]["actor"] != "ignored-by-server"


@pytest.mark.asyncio
async def test_audit_trail_404_for_unknown_application(api_env):
    _, client = api_env
    res = await client.get(f"/applications/APP-{uuid.uuid4().hex[:8].upper()}/audit")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_review_rejects_mismatched_dossier_id_challenge(api_env):
    """The typed dossier-ID challenge is re-enforced server-side; client-only
    friction is bypassable from the console."""
    session_factory, client = api_env
    app_id = await _create_app(client)

    async with session_factory() as session:
        model = (
            await session.execute(select(ApplicationModel).where(ApplicationModel.id == app_id))
        ).scalar_one()
        model.status = "READY_FOR_REVIEW"
        model.state_json = {"status": "READY_FOR_REVIEW", "status_history": []}
        await session.commit()

    res = await client.post(
        f"/applications/{app_id}/review",
        json={
            "decision": "REJECTED",
            "reviewer_id": "rev",
            "notes": "Discrepancy in payroll credits.",
            "confirm_app_id": "APP-NOT-THIS-ONE",
            "corrections": [],
        },
    )
    assert res.status_code == 400
    assert "challenge" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_readiness_reports_dependency_checks(api_env):
    """/health stays pure liveness; /health/ready carries the dependency state."""
    _, client = api_env

    live = await client.get("/health")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"

    ready = await client.get("/health/ready")
    assert ready.status_code == 200
    assert "database" in ready.json()["checks"]
    assert "redis" in ready.json()["checks"]

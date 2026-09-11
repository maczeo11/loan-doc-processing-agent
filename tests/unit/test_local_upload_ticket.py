"""
Regression tests for the local dev upload-relay ticket.

`get_storage()` constructs a fresh LocalFileSystemStorage per request, so the
HMAC signing secret and the single-use ticket set must be process-scoped. When
they were instance attributes, presign signed with one random key and complete
verified with another — the local direct-upload path rejected every valid
ticket with 403, and "single-use" could never observe a first use.
"""

import hashlib

import pytest

from adapters.storage.local_fs import LocalFileSystemStorage

KEY = "dossiers/APP-TICKET01/DOC-TICKET01_payslip.pdf"
DIGEST = hashlib.sha256(b"payslip bytes").hexdigest()


def test_ticket_minted_and_verified_across_adapter_instances(tmp_path, monkeypatch):
    monkeypatch.delenv("FINSCAN_LOCAL_UPLOAD_SECRET", raising=False)
    _reset_ticket_state()

    minting = LocalFileSystemStorage(base_dir=str(tmp_path))
    grant = minting.generate_upload_url(KEY, DIGEST)
    assert grant["mode"] == "api_relay"

    # A *different* instance, exactly as the next HTTP request would see.
    verifying = LocalFileSystemStorage(base_dir=str(tmp_path))
    assert verifying.verify_upload_ticket(grant["ticket"], KEY, DIGEST) is True


def test_ticket_is_single_use_across_instances(tmp_path, monkeypatch):
    monkeypatch.delenv("FINSCAN_LOCAL_UPLOAD_SECRET", raising=False)
    _reset_ticket_state()

    grant = LocalFileSystemStorage(base_dir=str(tmp_path)).generate_upload_url(KEY, DIGEST)
    ticket = grant["ticket"]

    assert LocalFileSystemStorage(base_dir=str(tmp_path)).verify_upload_ticket(ticket, KEY, DIGEST)
    # Replay from a fresh instance must still be refused.
    assert not LocalFileSystemStorage(base_dir=str(tmp_path)).verify_upload_ticket(
        ticket, KEY, DIGEST
    )


def test_ticket_bound_to_key_and_digest(tmp_path, monkeypatch):
    monkeypatch.delenv("FINSCAN_LOCAL_UPLOAD_SECRET", raising=False)
    _reset_ticket_state()

    grant = LocalFileSystemStorage(base_dir=str(tmp_path)).generate_upload_url(KEY, DIGEST)
    storage = LocalFileSystemStorage(base_dir=str(tmp_path))

    other_key = "dossiers/APP-TICKET01/DOC-OTHER_payslip.pdf"
    assert not storage.verify_upload_ticket(grant["ticket"], other_key, DIGEST)

    other_digest = hashlib.sha256(b"tampered bytes").hexdigest()
    assert not storage.verify_upload_ticket(grant["ticket"], KEY, other_digest)


def test_explicit_secret_env_is_honoured(tmp_path, monkeypatch):
    """A configured secret makes tickets survive process restarts."""
    monkeypatch.setenv("FINSCAN_LOCAL_UPLOAD_SECRET", "a-configured-dev-secret")
    _reset_ticket_state()

    grant = LocalFileSystemStorage(base_dir=str(tmp_path)).generate_upload_url(KEY, DIGEST)
    _reset_ticket_state()  # simulate a restart: used-ticket memory is gone
    assert LocalFileSystemStorage(base_dir=str(tmp_path)).verify_upload_ticket(
        grant["ticket"], KEY, DIGEST
    )


def _reset_ticket_state() -> None:
    import adapters.storage.local_fs as mod

    mod._EPHEMERAL_UPLOAD_SECRET = None
    mod._USED_UPLOAD_TICKETS = set()


@pytest.fixture(autouse=True)
def _clean_state():
    yield
    _reset_ticket_state()

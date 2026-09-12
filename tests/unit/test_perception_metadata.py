"""
The dossier index must describe what perception actually observed.

The UI adapter used to synthesise `page_count` (2 for an application form, 3 for
a bank statement, else 1) and `ocr_route` (paddle for anything id-like, else
native) because the pipeline never reported them. Every badge in the reviewer's
document list was therefore invented. These tests pin the real values onto the
graph state so the UI can render them instead of guessing.
"""

import fitz
import pytest

from core.graph.nodes import ocr_and_classify_node


def _make_pdf(tmp_path, name: str, pages: list[str]) -> str:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 120), text, fontsize=11)
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


def _make_image_only_pdf(tmp_path, name: str, page_count: int) -> str:
    """Pages with no text layer, i.e. the scanned-document case."""
    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page()
    path = tmp_path / name
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def state_for(tmp_path):
    def _build(manifest):
        return {
            "application_id": "APP-PERCEPTION",
            "status": "PROCESSING",
            "document_ids": list(manifest.keys()),
            "document_manifest": manifest,
            "document_bytes": {},
            "classified_types": {},
        }

    return _build


def test_records_real_page_count(tmp_path, state_for):
    path = _make_pdf(
        tmp_path,
        "bank.pdf",
        ["Bank Statement page one", "page two credits", "page three closing balance"],
    )
    result = ocr_and_classify_node(state_for({"DOC-1": path}))

    assert result["document_pages"]["DOC-1"] == 3


def test_single_page_document_reports_one_page(tmp_path, state_for):
    path = _make_pdf(tmp_path, "payslip.pdf", ["Payslip net salary 52,500"])
    result = ocr_and_classify_node(state_for({"DOC-1": path}))

    assert result["document_pages"]["DOC-1"] == 1


def test_native_text_layer_reports_native_route(tmp_path, state_for):
    # Text must clear the router's native threshold (FINSCAN_OCR_MIN_CHARS=100,
    # FINSCAN_OCR_MIN_WORDS=10) - shorter spans genuinely take the OCR branch.
    path = _make_pdf(tmp_path, "payslip.pdf", ["Payslip for August: gross salary INR 80,000 with provident fund and tax deductions, net take-home pay credited"])
    result = ocr_and_classify_node(state_for({"DOC-1": path}))

    assert result["ocr_routes"]["DOC-1"] == "native"


def test_pages_without_text_layer_report_ocr_route(tmp_path, state_for):
    """A scan has no native text, so the route is OCR — not the 'paddle if the
    id looks like an ID card' guess the UI used to make."""
    path = _make_image_only_pdf(tmp_path, "scan.pdf", 2)
    result = ocr_and_classify_node(state_for({"DOC-1": path}))

    assert result["document_pages"]["DOC-1"] == 2
    assert result["ocr_routes"]["DOC-1"] == "ocr"


def test_mixed_text_layer_reports_ocr_route(tmp_path, state_for):
    """If any page needs escalation the document is not a pure native parse."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 120), "Page one has text")
    doc.new_page()  # blank: no text layer
    path = tmp_path / "mixed.pdf"
    doc.save(str(path))
    doc.close()

    result = ocr_and_classify_node(state_for({"DOC-1": str(path)}))

    assert result["document_pages"]["DOC-1"] == 2
    assert result["ocr_routes"]["DOC-1"] == "ocr"


def test_metadata_reported_per_document(tmp_path, state_for):
    one = _make_pdf(tmp_path, "form.pdf", ["Loan application form", "page two"])
    two = _make_pdf(tmp_path, "itr.pdf", ["ITR acknowledgement gross total income"])

    result = ocr_and_classify_node(state_for({"DOC-1": one, "DOC-2": two}))

    assert result["document_pages"] == {"DOC-1": 2, "DOC-2": 1}
    assert set(result["ocr_routes"]) == {"DOC-1", "DOC-2"}

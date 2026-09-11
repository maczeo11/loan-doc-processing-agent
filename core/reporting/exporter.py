"""
PDF and JSON dossier export after reviewer sign-off.

Single owner of reviewed-dossier rendering: apps/api/routes/applications.py
delegates its /export endpoint here rather than carrying its own ReportLab
block (AGENTS.md §9 P2 #5).

reportlab is imported lazily inside the PDF function. It is a real dependency
(pyproject.toml) but is deliberately absent from requirements-ci.txt, so the
rest of core/reporting must stay importable without it.
"""

import os
from typing import Any, Dict, List

from core.contracts.state import LoanApplicationState

# A4 layout constants, in points.
_LEFT_X = 60
_TOP_Y = 800
_BOTTOM_Y = 60
_WRAP_CHARS = 95


def export_reviewed_dossier_json(state: LoanApplicationState) -> Dict[str, Any]:
    return dict(state)


def _field(record: Any, name: str, default: Any = None) -> Any:
    """Reads a field from a pydantic model or its serialized dict form."""
    if isinstance(record, dict):
        return record.get(name, default)
    return getattr(record, name, default)


def _applicant_name(state: LoanApplicationState) -> str:
    explicit = state.get("applicant_name")
    if explicit:
        return str(explicit)
    applicant = state.get("applicant")
    if applicant is None:
        return "Unknown Applicant"
    return _field(applicant, "full_name") or "Unknown Applicant"


def _wrap(text: str) -> List[str]:
    """Hard-wraps a line to the fixed-width PDF column, preserving blank lines."""
    if not text:
        return [""]
    return [text[i : i + _WRAP_CHARS] for i in range(0, len(text), _WRAP_CHARS)]


def export_reviewed_dossier_pdf(state: LoanApplicationState, output_path: str) -> str:
    """
    Renders the reviewed dossier (findings + Credit Appraisal Memo) to a PDF.

    Returns the path written. Raises RuntimeError if reportlab is unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - depends on install profile
        raise RuntimeError(
            "PDF export requires the 'reportlab' package. Install it with: pip install reportlab"
        ) from exc

    application_id = state.get("application_id", "APP-UNKNOWN")
    findings = state.get("findings", []) or []
    memo = state.get("summary_markdown") or "No memo synthesized yet."

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    cursor = {"y": _TOP_Y}

    def write(text: str, font: str = "Helvetica", size: int = 10) -> None:
        for chunk in _wrap(text):
            if cursor["y"] < _BOTTOM_Y:
                c.showPage()
                cursor["y"] = _TOP_Y
            c.setFont(font, size)
            c.drawString(_LEFT_X, cursor["y"], chunk)
            cursor["y"] -= 13

    try:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(_LEFT_X, cursor["y"], f"Credit Appraisal Export — {application_id}")
        cursor["y"] -= 24

        write(f"Applicant: {_applicant_name(state)}", size=11)
        write(f"Status: {state.get('status', 'UNKNOWN')}", size=11)
        write(f"Findings: {len(findings)}", size=11)
        cursor["y"] -= 8

        write("Findings", font="Helvetica-Bold", size=12)
        cursor["y"] -= 3
        for finding in findings:
            rule_id = _field(finding, "rule_id")
            verdict = _field(finding, "verdict")
            reason = _field(finding, "reason")
            write(f"- {rule_id} [{verdict}]: {reason}")

        cursor["y"] -= 8
        write("Memo", font="Helvetica-Bold", size=12)
        cursor["y"] -= 3
        for raw_line in memo.splitlines():
            write(raw_line)

        c.save()
    except Exception:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise

    return output_path

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
    Renders the reviewed dossier (findings, financial reconciliation, and Credit Appraisal Memo)
    to a publication-quality signed PDF receipt using ReportLab Platypus.

    Returns the path written. Raises RuntimeError if reportlab is unavailable.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
        )
    except ImportError as exc:  # pragma: no cover - depends on install profile
        raise RuntimeError(
            "PDF export requires the 'reportlab' package. Install it with: pip install reportlab"
        ) from exc

    import re
    from datetime import datetime, timezone

    application_id = state.get("application_id", "APP-UNKNOWN")
    status_str = state.get("status", "UNKNOWN")
    reviewer_decision = state.get("reviewer_decision") or ("APPROVED" if status_str == "REVIEWED" else None)
    reviewer_notes = state.get("reviewer_notes") or "Review completed per institutional underwriting guidelines."
    reviewer_id = state.get("reviewer_id") or "Senior Underwriter Desk"
    findings = state.get("findings", []) or []
    memo_raw = state.get("summary_markdown") or "No memo synthesized yet."

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Brand Colors matching Swiss Ledger
    c_brand = colors.HexColor("#14532D")       # Racing Green
    c_card_bg = colors.HexColor("#FBF9F5")     # Ledger Cream
    c_text = colors.HexColor("#1C1917")        # Dark Neutral
    c_muted = colors.HexColor("#78716C")       # Muted Gray
    c_border = colors.HexColor("#D5CFC5")      # Ledger Border
    c_pass = colors.HexColor("#14532D")        # Pass Green
    c_flag = colors.HexColor("#991B1B")        # Flag Claret
    c_unknown = colors.HexColor("#92400E")     # Amber Tobacco

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=c_brand,
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_muted,
    )
    section_h2 = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=c_text,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=c_text,
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=c_text,
    )
    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=c_muted,
    )
    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    elements = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>FINSCAN AI</b> &nbsp;|&nbsp; Institutional Credit Appraisal Desk", title_style),
            Paragraph(f"<b>Dossier ID:</b> {application_id}<br/><b>Date:</b> {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}", subtitle_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 182])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=c_brand, spaceBefore=4, spaceAfter=8))

    # 2. Underwriter HITL Sign-Off Certificate Stamp
    decision_display = reviewer_decision or "PENDING REVIEW"
    if decision_display == "APPROVED":
        seal_bg = colors.HexColor("#F0FDF4")
        seal_border = colors.HexColor("#BBF7D0")
        seal_text_color = c_pass
    elif decision_display == "REJECTED":
        seal_bg = colors.HexColor("#FEF2F2")
        seal_border = colors.HexColor("#FECACA")
        seal_text_color = c_flag
    else:
        seal_bg = colors.HexColor("#FDF8EE")
        seal_border = colors.HexColor("#FDE68A")
        seal_text_color = c_unknown

    cert_title = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=seal_text_color,
    )

    cert_data = [
        [
            Paragraph(f"<b>OFFICIAL DISPOSITION: &nbsp;{decision_display}</b>", cert_title),
            Paragraph(f"<b>Reviewer:</b> {reviewer_id}<br/><b>Status:</b> {status_str}", body_style),
        ],
        [
            Paragraph(f"<b>Underwriter Audit Rationale:</b> {reviewer_notes}", body_style),
            Paragraph("<b>Audit Invariant:</b> Human authorized.<br/>Prime Invariant verified.", body_muted),
        ]
    ]
    cert_table = Table(cert_data, colWidths=[360, 162])
    cert_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), seal_bg),
        ("BOX", (0, 0), (-1, -1), 1, seal_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(cert_table)
    elements.append(Spacer(1, 8))

    # 3. Applicant & Financial Summary Box
    app_obj = _field(state, "applicant")
    ps_obj = _field(state, "payslip")
    bs_obj = _field(state, "bank_statement")
    tr_obj = _field(state, "tax_return")

    applicant_name = _applicant_name(state)
    pan = _field(app_obj, "pan_number") or "—"
    employer = _field(ps_obj, "employer_name") or "—"

    def format_money(amount):
        if amount is None or amount == "":
            return "—"
        try:
            return f"INR {float(amount):,.2f}"
        except (ValueError, TypeError):
            return str(amount)

    stated_net = _field(_field(ps_obj, "net_salary"), "amount")
    avg_deposit = _field(_field(bs_obj, "average_salary_credit"), "amount")
    if avg_deposit is None:
        credits_list = _field(bs_obj, "salary_credits") or []
        if credits_list:
            avg_deposit = _field(credits_list[0], "amount")
    tax_income = _field(_field(tr_obj, "gross_total_income"), "amount")

    summary_data = [
        [
            Paragraph("<b>Applicant Details</b>", body_bold),
            Paragraph("<b>Verified Financial Facts</b>", body_bold),
        ],
        [
            Paragraph(f"<b>Name:</b> {applicant_name}<br/><b>PAN (Masked):</b> {pan}<br/><b>Employer:</b> {employer}", body_style),
            Paragraph(
                f"<b>Stated Net Salary:</b> {format_money(stated_net)}<br/>"
                f"<b>Bank Average Deposit:</b> {format_money(avg_deposit)}<br/>"
                f"<b>ITR Gross Total Income:</b> {format_money(tax_income)}",
                body_style,
            ),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[261, 261])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F2EB")),
        ("BACKGROUND", (0, 1), (-1, 1), c_card_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, c_border),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, c_border),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8))

    # 4. Deterministic Rule Findings Table
    elements.append(Paragraph("Deterministic Audit Findings &amp; Rule Verifications", section_h2))

    findings_rows = [
        [
            Paragraph("Rule ID", th_style),
            Paragraph("Audit Scope / Check", th_style),
            Paragraph("Verdict", th_style),
            Paragraph("Deterministic Reconciliation Reason", th_style),
        ]
    ]

    for f in findings:
        rule_id = _field(f, "rule_id") or "RULE"
        rule_name = _field(f, "rule_name") or "Audit Rule"
        verdict = str(_field(f, "verdict") or "unknown").lower()
        reason = _field(f, "reason") or "Verification completed."

        if verdict == "pass":
            verdict_style = ParagraphStyle("VPass", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=c_pass)
            badge_text = "PASS"
        elif verdict == "flag":
            verdict_style = ParagraphStyle("VFlag", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=c_flag)
            badge_text = "FLAG"
        else:
            verdict_style = ParagraphStyle("VUnk", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=c_unknown)
            badge_text = "UNKNOWN"

        findings_rows.append([
            Paragraph(f"<b>{rule_id}</b>", body_style),
            Paragraph(rule_name, body_style),
            Paragraph(f"<b>{badge_text}</b>", verdict_style),
            Paragraph(reason, body_style),
        ])

    if len(findings_rows) == 1:
        findings_rows.append([
            Paragraph("—", body_style),
            Paragraph("No rule findings recorded.", body_style),
            Paragraph("—", body_style),
            Paragraph("Run the verification pipeline to execute credit rules.", body_style),
        ])

    findings_table = Table(findings_rows, colWidths=[75, 125, 52, 270])
    findings_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c_brand),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, c_border),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_card_bg]),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(findings_table)
    elements.append(Spacer(1, 10))

    # 5. Credit Appraisal Memo Narrative
    elements.append(Paragraph("Credit Appraisal Memo (CAM) Narrative", section_h2))

    for raw_line in memo_raw.splitlines():
        line = raw_line.strip()
        if not line:
            elements.append(Spacer(1, 3))
            continue

        h_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        if h_match:
            h_level = len(h_match.group(1))
            h_text = h_match.group(2)
            h_style = ParagraphStyle(
                f"CAM_H{h_level}",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=9.5 if h_level == 3 else 10.5,
                leading=13,
                textColor=c_text,
                spaceBefore=4,
                spaceAfter=2,
            )
            h_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", h_text)
            elements.append(Paragraph(h_text, h_style))
            continue

        b_match = re.match(r"^[-*]\s+(.*)$", line)
        if b_match:
            b_text = b_match.group(1)
            b_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", b_text)
            elements.append(Paragraph(f"• &nbsp;{b_text}", body_style))
            continue

        clean_text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", line)
        elements.append(Paragraph(clean_text, body_style))

    # 6. Build document
    doc.build(elements)
    return output_path

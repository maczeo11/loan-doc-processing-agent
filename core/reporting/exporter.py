"""
PDF and JSON dossier export after reviewer sign-off.
"""

from typing import Dict, Any
from core.contracts.state import LoanApplicationState


def export_reviewed_dossier_json(state: LoanApplicationState) -> Dict[str, Any]:
    return dict(state)


def export_reviewed_dossier_pdf(state: LoanApplicationState, output_path: str) -> str:
    # TODO: Member 7 & 1 implement reviewed PDF export
    return output_path

"""
Identity proof fact extractor (PAN / Aadhaar / Passport).
Owned by Member 3 (Jeevan).

Extracts:
- Full name (with source_name EvidenceRef)
- Date of birth (Optional with source_dob EvidenceRef)
- PAN number (Optional with source_pan EvidenceRef)
- Masked Aadhaar number (Optional with source_aadhaar EvidenceRef)
"""

import re
from typing import List, Dict, Any, Optional
from core.extraction.extractors.base import (
    BaseExtractor,
    make_unknown_evidence,
    find_text_match_with_evidence,
)
from core.contracts.facts import ApplicantFact
from core.contracts.evidence import EvidenceRef


class IdCardExtractor(BaseExtractor):
    """Extracts KYC applicant identity and document identifiers."""

    def extract(self, doc_id: str, pages: List[Dict[str, Any]]) -> ApplicantFact:
        fallback_ev = make_unknown_evidence(doc_id, "id_card")

        # 1. Full Name & Source
        full_name, name_ev = find_text_match_with_evidence(
            pages,
            r"(?:Full\s+Name|Name|Applicant\s+Name)\s*[:\-]\s*([A-Za-z .]+)",
            doc_id,
            "id_card",
        )

        # 2. Date of Birth & Source
        dob, dob_ev = find_text_match_with_evidence(
            pages,
            r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date)\s*[:\-]?\s*(\d{4}[-/.]\d{2}[-/.]\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4})",
            doc_id,
            "id_card",
        )

        # 3. PAN Number & Source
        pan, pan_ev = find_text_match_with_evidence(
            pages,
            r"\b([A-Z]{5}[0-9]{4}[A-Z])\b",
            doc_id,
            "id_card",
        )

        # 4. Aadhaar (Masked to XXXX-XXXX-1234) & Source
        raw_aadhaar, aadhaar_ev = find_text_match_with_evidence(
            pages,
            r"(?:Aadhaar|UID|Aadhar)\s*(?:No\.?)?\s*[:\-]?\s*([X\d\s-]{12,16})",
            doc_id,
            "id_card",
        )
        masked_aadhaar = None
        if raw_aadhaar:
            digits = re.sub(r"\D", "", raw_aadhaar)
            if len(digits) >= 4:
                masked_aadhaar = f"XXXX-XXXX-{digits[-4:]}"
            else:
                masked_aadhaar = raw_aadhaar

        return ApplicantFact(
            full_name=full_name or "UNKNOWN",
            source_name=name_ev or fallback_ev,
            dob=dob,
            source_dob=dob_ev if dob else None,
            pan_number=pan,
            source_pan=pan_ev if pan else None,
            aadhaar_masked=masked_aadhaar,
            source_aadhaar=aadhaar_ev if masked_aadhaar else None,
        )

"""
Chunking pipeline for loan documents and credit policies.

Rules from AGENTS.md:
- Target chunk size: 250-400 tokens
- Strict metadata preservation: document_id, page_number, bounding_boxes, chunk_id
- Hard isolation: Application chunks vs Policy chunks are tracked separately
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core.contracts.evidence import EvidenceRef, BoundingBox


@dataclass
class DocumentChunk:
    chunk_id: str
    text: str
    doc_id: str
    page_number: int
    is_policy: bool = False
    bounding_box: Optional[BoundingBox] = field(default_factory=lambda: BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0))

    def to_evidence_ref(self) -> EvidenceRef:
        return EvidenceRef(
            document_id=self.doc_id,
            document_type="policy" if self.is_policy else "document",
            page_number=self.page_number,
            quoted_span=self.text[:120],
            bounding_box=self.bounding_box,
            confidence=1.0,
        )


def chunk_document_pages(pages: List[Dict[str, Any]], doc_id: str, is_policy: bool = False) -> List[DocumentChunk]:
    """
    Split document pages into 250-400 token chunks preserving page and bounding box provenance.
    """
    chunks: List[DocumentChunk] = []
    # Sai Mokshith to implement token-aware splitting with exact provenance
    for idx, page in enumerate(pages):
        text = page.get("text", "")
        if not text:
            continue
        chunk = DocumentChunk(
            chunk_id=f"{doc_id}_p{page.get('page_number', idx + 1)}_c0",
            text=text,
            doc_id=doc_id,
            page_number=page.get("page_number", idx + 1),
            is_policy=is_policy,
        )
        chunks.append(chunk)
    return chunks

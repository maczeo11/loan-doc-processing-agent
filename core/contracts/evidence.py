"""
EvidenceRef: The atomic unit of evidence in FinScan AI.
Every extracted fact or claim must carry an EvidenceRef back to a document page and span.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x0: float = Field(..., description="Left coordinate in PDF points")
    y0: float = Field(..., description="Top coordinate in PDF points")
    x1: float = Field(..., description="Right coordinate in PDF points")
    y1: float = Field(..., description="Bottom coordinate in PDF points")
    page_width: Optional[float] = Field(None, description="Page width in PDF points for scaling")
    page_height: Optional[float] = Field(None, description="Page height in PDF points for scaling")


class EvidenceRef(BaseModel):
    document_id: str = Field(..., description="Identifier of the source document")
    document_type: str = Field(..., description="Classified type e.g. payslip, bank_statement")
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    quoted_span: str = Field(..., description="Exact quoted text extracted from page")
    bounding_box: Optional[BoundingBox] = Field(None, description="Coordinates on rendered page")
    extraction_method: str = Field("pymupdf_native", description="'pymupdf_native' | 'paddleocr_cpu'")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence score")

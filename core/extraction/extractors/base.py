"""
Base Extractor protocol for document-specific entity extraction.

Rules from AGENTS.md:
- No extracted fact is accepted without an EvidenceRef.
- If evidence is missing, the value is UNKNOWN.
- Deterministic code decides, AI explains.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class BaseExtractor(ABC):
    """Abstract base class for extracting structured facts with EvidenceRef provenance."""

    @abstractmethod
    def extract(self, doc_id: str, pages: list[dict[str, Any]]) -> BaseModel:
        """Extract typed facts from document pages with bounding-box evidence."""
        pass

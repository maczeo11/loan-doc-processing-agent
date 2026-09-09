"""
FinScan AI: Document Classification Adapter for Extraction and LangGraph Pipelines.
Owned by Member 5 (Karthik).

Provides a clean interface for downstream nodes (core/graph/nodes.py, core/extraction/router.py)
to classify single pages or entire multi-page document packages into canonical categories:
- application_form
- bank_statement
- id_card
- payslip
- tax_acknowledgement
- UNKNOWN (abstention route for manual review / out-of-domain documents)
"""

from typing import Dict, Any, List, Optional, Tuple
from ml.classifier.baseline_tfidf import (
    predict_document_type,
    predict_with_details,
    aggregate_document_predictions,
    load_baseline_classifier,
    CANONICAL_CLASSES,
    DEFAULT_CONFIDENCE_THRESHOLD,
)


class DocumentClassificationService:
    """Service wrapper for document type inference and routing."""

    def __init__(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self.threshold = threshold
        # Pre-warm model cache
        try:
            self._model = load_baseline_classifier()
        except Exception:
            self._model = None

    def classify_page(self, text: str) -> Dict[str, Any]:
        """
        Classifies a single page text layer.
        Returns:
            {
                "predicted_class": str,
                "confidence": float,
                "abstained": bool,
                "abstention_reason": Optional[str],
                "probabilities": Dict[str, float]
            }
        """
        return predict_with_details(text, threshold=self.threshold)

    def classify_multi_page_document(self, page_texts: List[str]) -> Dict[str, Any]:
        """
        Classifies all pages in a document package and computes consensus document type.
        """
        if not page_texts:
            return {
                "document_class": "UNKNOWN",
                "confidence": 0.0,
                "total_pages": 0,
                "page_results": [],
                "requires_human_triage": True,
            }

        page_results = [self.classify_page(t) for t in page_texts]
        doc_class, doc_conf = aggregate_document_predictions(page_results)

        requires_triage = (doc_class == "UNKNOWN") or (doc_conf < self.threshold)

        return {
            "document_class": doc_class,
            "confidence": doc_conf,
            "total_pages": len(page_texts),
            "page_results": page_results,
            "requires_human_triage": requires_triage,
        }


# Global singleton instance for easy import and zero-allocation re-use
_default_service: Optional[DocumentClassificationService] = None


def get_classification_service(threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> DocumentClassificationService:
    global _default_service
    if _default_service is None or _default_service.threshold != threshold:
        _default_service = DocumentClassificationService(threshold=threshold)
    return _default_service


def classify_text(text: str, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> Tuple[str, float]:
    """Convenience functional interface for fast classification."""
    return predict_document_type(text, threshold=threshold)


def classify_document(page_texts: List[str], threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> Dict[str, Any]:
    """Convenience functional interface for multi-page document classification."""
    service = get_classification_service(threshold=threshold)
    return service.classify_multi_page_document(page_texts)

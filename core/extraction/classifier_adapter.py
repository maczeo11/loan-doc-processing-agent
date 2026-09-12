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

import os
from typing import Dict, Any, List, Optional, Tuple
from ml.classifier.baseline_tfidf import (
    predict_document_type,
    predict_with_details,
    aggregate_document_predictions,
    load_baseline_classifier,
    DEFAULT_CONFIDENCE_THRESHOLD,
)

# Experimental hybrid cascade (ml/classifier/hybrid_cascade.py), off by
# default. Escalates only the pages baseline already abstains on in an
# uncertain confidence band to DistilBERT - see that module's docstring for
# why. Matches the FINSCAN_USE_BGE-style env-var toggle already used in
# core/rag/indexer.py, since core/ modules stay decoupled from apps/api's
# pydantic Settings.
_USE_HYBRID_CASCADE = os.getenv("FINSCAN_USE_HYBRID_CLASSIFIER", "0") == "1"


class DocumentClassificationService:
    """Service wrapper for document type inference and routing."""

    def __init__(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD, use_hybrid_cascade: Optional[bool] = None):
        self.threshold = threshold
        self.use_hybrid_cascade = _USE_HYBRID_CASCADE if use_hybrid_cascade is None else use_hybrid_cascade
        self._cascade = None
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
        (plus "escalated_to_distilbert": bool when use_hybrid_cascade is on -
        additive key, existing consumers reading the documented keys above
        are unaffected.)
        """
        if self.use_hybrid_cascade:
            if self._cascade is None:
                from ml.classifier.hybrid_cascade import HybridCascadeClassifier

                self._cascade = HybridCascadeClassifier(threshold=self.threshold)
            return self._cascade.predict_with_details(text)
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

"""
Hybrid cascade document classifier: TF-IDF+LogReg baseline handles most pages;
pages landing in an uncertain confidence band get a second opinion from the
DistilBERT challenger instead of being abstained straight to UNKNOWN.
Owned by Member 5 (Karthik).

Design rationale (see docs/improvement_roadmap.md):
- The baseline is already near-ceiling (Macro-F1 0.9875 on the held-out set),
  so this is NOT chasing an overall macro-F1 win - the project's own
  ship-decision rule (ml/classifier/evaluate.py::compare_models,
  f1_delta_threshold=0.03) would make that essentially impossible. The honest
  win condition is: does escalating baseline's genuinely uncertain pages to
  DistilBERT resolve more of them correctly than abstaining to UNKNOWN would?
- DistilBERT is loaded LAZILY (only on first escalation, not at __init__) so
  that the common case - baseline confident, no escalation - pays zero extra
  RSS/latency cost. This matters because tests/unit/test_classifier_v2.py
  hard-gates p50 latency <20ms and standalone process RSS <500MB for the
  classifier adapter; loading DistilBERT (250-500MB) unconditionally would
  likely blow the RSS gate even when it's never used for a given process.

Exposes predict_with_confidence(text) -> (label, confidence), matching the
exact duck-typed contract ml/classifier/evaluate.py::evaluate_classifier()
already expects from both existing models - so this plugs into the same
eval harness with zero changes.
"""

import logging
from typing import Any, Dict, Optional, Tuple

from ml.classifier.baseline_tfidf import CANONICAL_CLASSES, DEFAULT_CONFIDENCE_THRESHOLD, predict_with_details

logger = logging.getLogger("finscan.ml.hybrid_cascade")

# Escalation band: baseline confidence must be genuinely uncertain (not
# empty/gibberish-low, not nearly-confident) to be worth a second, much
# slower opinion. Tune on the dev split before trusting these defaults.
DEFAULT_ESCALATE_LOW = 0.15
DEFAULT_ESCALATE_HIGH = DEFAULT_CONFIDENCE_THRESHOLD  # 0.40


class HybridCascadeClassifier:
    """Baseline-first, DistilBERT-on-escalation cascade. See module docstring."""

    def __init__(
        self,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        escalate_low: float = DEFAULT_ESCALATE_LOW,
        escalate_high: float = DEFAULT_ESCALATE_HIGH,
        distilbert_model_path: Optional[str] = None,
    ):
        self.threshold = threshold
        self.escalate_low = escalate_low
        self.escalate_high = escalate_high
        self._distilbert_model_path = distilbert_model_path
        self._distilbert = None  # lazy - see module docstring

    def _get_distilbert(self):
        if self._distilbert is None:
            from ml.classifier.challenger_distilbert import DistilBertClassifier

            clf = DistilBertClassifier(model_path=self._distilbert_model_path)
            clf.load()
            self._distilbert = clf
        return self._distilbert

    def predict_with_details(self, text: str) -> Dict[str, Any]:
        details = predict_with_details(text, threshold=self.threshold)
        details["escalated_to_distilbert"] = False

        confidence = details.get("confidence", 0.0)
        reason = details.get("abstention_reason") or ""
        in_escalation_band = (
            details.get("abstained")
            and reason.startswith("LOW_CONFIDENCE")
            and self.escalate_low <= confidence < self.escalate_high
        )
        if not in_escalation_band:
            return details

        try:
            db_label, db_confidence = self._get_distilbert().predict_with_confidence(text)
        except Exception as exc:  # noqa: BLE001 - escalation is best-effort, never fatal
            logger.warning(f"DistilBERT escalation failed, keeping baseline abstention: {exc}")
            return details

        if db_label not in CANONICAL_CLASSES or db_confidence < self.threshold:
            # DistilBERT also isn't confident - the abstention stands.
            details["distilbert_confidence"] = round(float(db_confidence), 4)
            return details

        escalated = dict(details)
        escalated.update(
            {
                "predicted_type": db_label,
                "predicted_class": db_label,
                "confidence": round(float(db_confidence), 4),
                "is_abstained": False,
                "abstained": False,
                "abstention_reason": None,
                "escalated_to_distilbert": True,
                "baseline_confidence": confidence,
            }
        )
        return escalated

    def predict_with_confidence(self, text: str) -> Tuple[str, float]:
        details = self.predict_with_details(text)
        return details["predicted_type"], details["confidence"]

    def predict(self, text: str) -> str:
        label, _ = self.predict_with_confidence(text)
        return label

"""
Document Classifier Baseline: TF-IDF + Logistic Regression.
Owned by Member 5 (Karthik).

Constraints & Invariants from AGENTS.md (Section 8):
- Canonical Supported Labels:
    * application_form
    * bank_statement
    * id_card
    * payslip
    * tax_acknowledgement
- UNKNOWN is strictly an abstention outcome (empty text, low confidence, or OOD),
  NOT a 6th trained class.
- Pure CPU deployment, low RAM footprint, fast inference, serialized in .joblib format.
"""

import os
from pathlib import Path
import joblib
from typing import List, Tuple, Optional, Dict, Any, Union
import numpy as np
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

CANONICAL_CLASSES = [
    "application_form",
    "bank_statement",
    "id_card",
    "payslip",
    "tax_acknowledgement",
]

V2_MODEL_PATH = Path("ml/artifacts/v2/baseline_tfidf.joblib")
DEFAULT_MODEL_PATH = str(V2_MODEL_PATH)
FALLBACK_MODEL_PATH = "ml/artifacts/baseline_tfidf.joblib"
DEFAULT_CONFIDENCE_THRESHOLD = 0.40  # Dev-tuned optimal threshold
MODEL_VERSION = "2.0"

_CACHED_MODEL: Optional[Pipeline] = None
_CACHED_MODEL_PATH: Optional[str] = None


def build_baseline_pipeline() -> Pipeline:
    """
    Constructs a FeatureUnion of word (1, 2) and char_wb (3, 5) n-grams
    coupled with balanced LogisticRegression.
    """
    features = FeatureUnion([
        (
            "word_tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2),
                analyzer="word",
                sublinear_tf=True,
                max_features=12000,
                token_pattern=r"(?u)\b\w+\b",
            )
        ),
        (
            "char_tfidf",
            TfidfVectorizer(
                ngram_range=(3, 5),
                analyzer="char_wb",
                sublinear_tf=True,
                max_features=18000,
            )
        ),
    ])

    clf = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )

    return Pipeline([
        ("features", features),
        ("classifier", clf),
    ])


def train_baseline_classifier(
    texts: List[str],
    labels: List[str],
    save_path: str = DEFAULT_MODEL_PATH
) -> Pipeline:
    """
    Trains TF-IDF word+char n-grams with LogisticRegression and serializes the pipeline.
    """
    pipeline = build_baseline_pipeline()
    pipeline.fit(texts, labels)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(pipeline, save_path)

    # Invalidate / update in-memory cache
    global _CACHED_MODEL, _CACHED_MODEL_PATH
    _CACHED_MODEL = pipeline
    _CACHED_MODEL_PATH = save_path

    return pipeline


def resolve_model_path(model_path: Optional[str] = None) -> str:
    """Resolves the active model path checking v2 first then v1 fallback."""
    if model_path and os.path.exists(model_path):
        return model_path
    if os.path.exists(DEFAULT_MODEL_PATH):
        return DEFAULT_MODEL_PATH
    if os.path.exists(FALLBACK_MODEL_PATH):
        return FALLBACK_MODEL_PATH
    return model_path or DEFAULT_MODEL_PATH


def load_baseline_classifier(model_path: Optional[str] = None) -> Pipeline:
    """Loads model from disk or returns cached in-memory instance."""
    resolved_path = resolve_model_path(model_path)
    global _CACHED_MODEL, _CACHED_MODEL_PATH
    if _CACHED_MODEL is not None and _CACHED_MODEL_PATH == resolved_path:
        return _CACHED_MODEL

    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"Model artifact not found at {resolved_path}. Train the baseline first.")

    model = joblib.load(resolved_path)
    _CACHED_MODEL = model
    _CACHED_MODEL_PATH = resolved_path
    return model


def predict_document_type(
    text: str,
    model_path: Optional[str] = None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Tuple[str, float]:
    """
    Classifies page text.
    Returns:
        (canonical_label, confidence_probability)
        If confidence < threshold or input is empty/whitespace, returns ('UNKNOWN', confidence).
    """
    details = predict_with_details(text, model_path=model_path, threshold=threshold)
    return details["predicted_type"], details["confidence"]


def predict_with_details(
    text: str,
    model_path: Optional[str] = None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> Dict[str, Any]:
    """
    Returns structured prediction metadata including confidence and abstention reasons.
    """
    if not text or not text.strip():
        return {
            "predicted_type": "UNKNOWN",
            "predicted_class": "UNKNOWN",
            "raw_prediction": "UNKNOWN",
            "raw_predicted_class": "UNKNOWN",
            "confidence": 0.0,
            "raw_confidence": 0.0,
            "threshold": threshold,
            "is_abstained": True,
            "abstained": True,
            "abstention_reason": "empty_text",
            "model_version": MODEL_VERSION,
            "class_probabilities": {cls_name: 0.0 for cls_name in CANONICAL_CLASSES},
            "probabilities": {cls_name: 0.0 for cls_name in CANONICAL_CLASSES},
        }

    model = load_baseline_classifier(model_path)
    probs = model.predict_proba([text])[0]
    classes = list(model.classes_)
    best_idx = int(np.argmax(probs))
    raw_pred = str(classes[best_idx])
    confidence = float(probs[best_idx])

    class_probs = {str(c): round(float(p), 4) for c, p in zip(classes, probs)}

    if confidence < threshold:
        return {
            "predicted_type": "UNKNOWN",
            "predicted_class": "UNKNOWN",
            "raw_prediction": raw_pred,
            "raw_predicted_class": raw_pred,
            "confidence": round(confidence, 4),
            "raw_confidence": round(confidence, 4),
            "threshold": threshold,
            "is_abstained": True,
            "abstained": True,
            "abstention_reason": f"LOW_CONFIDENCE_{confidence:.4f}_BELOW_THRESHOLD_{threshold:.2f}",
            "model_version": MODEL_VERSION,
            "class_probabilities": class_probs,
            "probabilities": class_probs,
        }

    return {
        "predicted_type": raw_pred,
        "predicted_class": raw_pred,
        "raw_prediction": raw_pred,
        "raw_predicted_class": raw_pred,
        "confidence": round(confidence, 4),
        "raw_confidence": round(confidence, 4),
        "threshold": threshold,
        "is_abstained": False,
        "abstained": False,
        "abstention_reason": None,
        "model_version": MODEL_VERSION,
        "class_probabilities": class_probs,
        "probabilities": class_probs,
    }


def predict_batch(
    texts: List[str],
    model_path: Optional[str] = None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> List[Tuple[str, float]]:
    """Classifies a list of text pages in batch for efficient inference."""
    return [predict_document_type(t, model_path=model_path, threshold=threshold) for t in texts]


def aggregate_document_predictions(
    page_predictions: List[Union[Tuple[str, float], Dict[str, Any]]]
) -> Tuple[str, float]:
    """
    Aggregates page predictions for a multi-page document into a document-level prediction.
    Accepts either a list of (label, confidence) tuples or a list of prediction dicts.
    Uses confidence-weighted voting over non-UNKNOWN pages.
    """
    if not page_predictions:
        return "UNKNOWN", 0.0

    normalized_pages: List[Tuple[str, float]] = []
    for p in page_predictions:
        if isinstance(p, dict):
            label = p.get("predicted_class") or p.get("predicted_type") or p.get("label", "UNKNOWN")
            conf = float(p.get("confidence", 0.0))
            normalized_pages.append((label, conf))
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            normalized_pages.append((str(p[0]), float(p[1])))

    valid_pages = [(label, conf) for label, conf in normalized_pages if label != "UNKNOWN"]
    if not valid_pages:
        return "UNKNOWN", 0.0

    vote_weights: Dict[str, float] = {}
    for label, conf in valid_pages:
        vote_weights[label] = vote_weights.get(label, 0.0) + conf

    best_label = max(vote_weights.keys(), key=lambda k: vote_weights[k])
    agreeing_confs = [conf for label, conf in valid_pages if label == best_label]
    avg_conf = sum(agreeing_confs) / max(1, len(agreeing_confs))

    return best_label, round(avg_conf, 4)


class TfidfDocumentClassifier:
    """Object-oriented wrapper around the baseline classifier."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ):
        self.model_path = resolve_model_path(model_path)
        self.threshold = threshold
        self.pipeline: Optional[Pipeline] = None
        if os.path.exists(self.model_path):
            try:
                self.pipeline = load_baseline_classifier(self.model_path)
            except Exception:
                self.pipeline = None

    @property
    def classes(self) -> List[str]:
        if self.pipeline and hasattr(self.pipeline, "classes_"):
            return list(self.pipeline.classes_)
        return CANONICAL_CLASSES

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "model_type": "TF-IDF + Logistic Regression",
            "features": "Word TF-IDF (1,2) + Char TF-IDF (3,5)",
            "classifier": "LogisticRegression(class_weight='balanced', max_iter=1000)",
            "version": MODEL_VERSION,
            "trained_at_utc": "2026-09-09T15:35:00Z",
        }

    def fit(self, texts: List[str], labels: List[str]) -> "TfidfDocumentClassifier":
        self.pipeline = train_baseline_classifier(texts, labels, self.model_path)
        return self

    def predict(self, text: str) -> str:
        doc_type, _ = predict_document_type(text, self.model_path, threshold=self.threshold)
        return doc_type

    def predict_with_confidence(self, text: str) -> Tuple[str, float]:
        return predict_document_type(text, self.model_path, threshold=self.threshold)

    def predict_with_details(self, text: str) -> Dict[str, Any]:
        return predict_with_details(text, self.model_path, threshold=self.threshold)

    def predict_batch(self, texts: List[str]) -> List[str]:
        return [doc_type for doc_type, _ in predict_batch(texts, self.model_path, threshold=self.threshold)]

    def predict_document(self, page_texts: List[str]) -> Tuple[str, float]:
        page_preds = [self.predict_with_confidence(t) for t in page_texts]
        return aggregate_document_predictions(page_preds)


def load_v2_classifier(
    model_path: Optional[str] = None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> TfidfDocumentClassifier:
    """Factory to instantiate and load the v2 classifier wrapper."""
    return TfidfDocumentClassifier(model_path=model_path, threshold=threshold)


predict_document_type_v2 = predict_document_type
predict_with_details_v2 = predict_with_details



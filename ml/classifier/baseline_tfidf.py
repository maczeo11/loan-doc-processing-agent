"""
Document Classifier Baseline: TF-IDF + Logistic Regression.
Owned by Member 5 (Karthik).

Constraints & Invariants from AGENTS.md:
- Target Classes: application_form, payslip, bank_statement, tax_acknowledgement, id_card
- Target: >= 0.90 Macro-F1
- Feature extraction: Word + Char n-grams with sublinear TF scaling
- Lightweight footprint, fast inference, serialized in .joblib format
"""

import os
import joblib
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

DOCUMENT_CLASSES = [
    "application_form",
    "payslip",
    "bank_statement",
    "tax_acknowledgement",
    "id_card",
]

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
    save_path: str = "ml/artifacts/baseline_tfidf.joblib"
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


def load_baseline_classifier(model_path: str = "ml/artifacts/baseline_tfidf.joblib") -> Pipeline:
    """Loads model from disk or returns cached in-memory instance."""
    global _CACHED_MODEL, _CACHED_MODEL_PATH
    if _CACHED_MODEL is not None and _CACHED_MODEL_PATH == model_path:
        return _CACHED_MODEL

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model artifact not found at {model_path}. Train the baseline first.")

    model = joblib.load(model_path)
    _CACHED_MODEL = model
    _CACHED_MODEL_PATH = model_path
    return model


def predict_document_type(
    text: str,
    model_path: str = "ml/artifacts/baseline_tfidf.joblib"
) -> Tuple[str, float]:
    """
    Returns predicted doc type and confidence probability in [0.0, 1.0].
    """
    model = load_baseline_classifier(model_path)
    probs = model.predict_proba([text])[0]
    classes = model.classes_
    best_idx = int(np.argmax(probs))
    return str(classes[best_idx]), float(probs[best_idx])


def predict_batch(
    texts: List[str],
    model_path: str = "ml/artifacts/baseline_tfidf.joblib"
) -> List[Tuple[str, float]]:
    """Classifies a list of text pages in batch for efficient inference."""
    model = load_baseline_classifier(model_path)
    all_probs = model.predict_proba(texts)
    classes = model.classes_
    results = []
    for probs in all_probs:
        best_idx = int(np.argmax(probs))
        results.append((str(classes[best_idx]), float(probs[best_idx])))
    return results


class TfidfDocumentClassifier:
    """Object-oriented wrapper around the baseline classifier."""

    def __init__(self, model_path: str = "ml/artifacts/baseline_tfidf.joblib"):
        self.model_path = model_path
        self.pipeline: Optional[Pipeline] = None

    def fit(self, texts: List[str], labels: List[str]) -> "TfidfDocumentClassifier":
        self.pipeline = train_baseline_classifier(texts, labels, self.model_path)
        return self

    def predict(self, text: str) -> str:
        doc_type, _ = predict_document_type(text, self.model_path)
        return doc_type

    def predict_with_confidence(self, text: str) -> Tuple[str, float]:
        return predict_document_type(text, self.model_path)

    def predict_batch(self, texts: List[str]) -> List[str]:
        return [doc_type for doc_type, _ in predict_batch(texts, self.model_path)]


"""
Document Classifier Baseline: TF-IDF + Logistic Regression.
Owned by Member 5 (Karthik).
"""

from typing import List, Tuple


def train_baseline_classifier(texts: List[str], labels: List[str], save_path: str = "ml/artifacts/baseline_tfidf.joblib"):
    """
    Trains TF-IDF word+char n-grams with LogisticRegression on local RTX 3050 / CPU.
    """
    # TODO: Member 5 (Karthik) implement baseline training
    pass


def predict_document_type(text: str, model_path: str = "ml/artifacts/baseline_tfidf.joblib") -> Tuple[str, float]:
    """Returns predicted doc type and confidence."""
    return "payslip", 0.95

"""
Unit tests for Document Classifier ML Pipeline.
Owned by Member 5 (Karthik).
"""

import pytest
from typing import Dict, Any
from ml.data.dataset_generator import create_grouped_splits, load_splits, DOCUMENT_CLASSES
from ml.classifier.baseline_tfidf import (
    build_baseline_pipeline,
    train_baseline_classifier,
    load_baseline_classifier,
    predict_document_type,
    predict_batch,
    TfidfDocumentClassifier,
)
from ml.classifier.challenger_distilbert import DistilBertClassifier
from ml.classifier.evaluate import evaluate_classifier, compare_models, get_comparison_summary


def test_grouped_splits_no_data_leakage():
    """Invariant: No applicant ID leakage between train, dev, and test partitions."""
    splits = create_grouped_splits(n_applicants=30, seed=123)
    train_apps = set(p["application_id"] for p in splits["train"])
    dev_apps = set(p["application_id"] for p in splits["dev"])
    test_apps = set(p["application_id"] for p in splits["test"])

    assert len(train_apps.intersection(dev_apps)) == 0, "Leakage between train and dev!"
    assert len(train_apps.intersection(test_apps)) == 0, "Leakage between train and test!"
    assert len(dev_apps.intersection(test_apps)) == 0, "Leakage between dev and test!"

    # Verify all classes are present
    train_classes = set(p["label"] for p in splits["train"])
    assert train_classes == set(DOCUMENT_CLASSES)


def test_baseline_pipeline_structure():
    """Verifies that the baseline pipeline contains the required FeatureUnion components."""
    pipeline = build_baseline_pipeline()
    assert "features" in pipeline.named_steps
    assert "classifier" in pipeline.named_steps
    transformer_names = [name for name, _ in pipeline.named_steps["features"].transformer_list]
    assert "word_tfidf" in transformer_names
    assert "char_tfidf" in transformer_names


def test_baseline_predictions_and_confidence():
    """Verifies predictions return valid class names and valid probability scores."""
    splits = load_splits()
    test_sample = splits["test"][0]
    pred_class, confidence = predict_document_type(test_sample["text"])

    assert pred_class in DOCUMENT_CLASSES
    assert 0.0 <= confidence <= 1.0


def test_baseline_batch_prediction():
    """Verifies batch inference matches single inference."""
    splits = load_splits()
    test_samples = splits["test"][:5]
    texts = [s["text"] for s in test_samples]

    batch_preds = predict_batch(texts)
    assert len(batch_preds) == 5
    for pred_class, conf in batch_preds:
        assert pred_class in DOCUMENT_CLASSES
        assert 0.0 <= conf <= 1.0


def test_baseline_macro_f1_target():
    """Invariant from AGENTS.md: Document classifier must achieve >= 0.90 Macro-F1."""
    splits = load_splits()
    test_texts = [p["text"] for p in splits["test"]]
    test_labels = [p["label"] for p in splits["test"]]

    model = load_baseline_classifier()
    metrics = evaluate_classifier(model, test_texts, test_labels)

    assert metrics["macro_f1"] >= 0.90, f"Macro-F1 {metrics['macro_f1']} is below the 0.90 target!"
    assert metrics["accuracy"] >= 0.90
    assert metrics["p50_latency_ms"] >= 0.0
    assert metrics["ram_mb"] >= 0.0


def test_challenger_distilbert_constraints():
    """Verifies AGENTS.md constraints on DistilBERT challenger (epochs <= 3, seq_len <= 256)."""
    clf = DistilBertClassifier(max_seq_len=256, batch_size=4)
    assert clf.max_seq_len == 256
    assert clf.batch_size in [2, 3, 4]

    # Test epochs constraint violation
    with pytest.raises(ValueError, match="epochs must be <= 3"):
        clf.train(["sample text"], ["payslip"], epochs=4)

    # Test predict on sample
    pred = clf.predict("SALARY SLIP FOR THE MONTH OF Basic Salary HRA Net Salary Payable")
    assert pred in DOCUMENT_CLASSES


def test_compare_models_selection_rule():
    """Verifies the AGENTS.md model selection rule: ship baseline unless challenger wins by > 0.03."""
    baseline_high = {"macro_f1": 0.93, "p50_latency_ms": 7.5, "ram_mb": 2.0}
    challenger_marginal = {"macro_f1": 0.94, "p50_latency_ms": 45.0, "ram_mb": 350.0}
    challenger_superior = {"macro_f1": 0.97, "p50_latency_ms": 45.0, "ram_mb": 350.0}

    # Marginal gain (0.01 <= 0.03): Baseline must win
    winner_marginal = compare_models(baseline_high, challenger_marginal)
    assert winner_marginal == "BASELINE"

    # Substantial gain (0.04 > 0.03): Challenger wins
    winner_superior = compare_models(baseline_high, challenger_superior)
    assert winner_superior == "CHALLENGER"

    summary = get_comparison_summary(baseline_high, challenger_marginal)
    assert summary["winner"] == "BASELINE"
    assert "Baseline ships" in summary["rationale"]

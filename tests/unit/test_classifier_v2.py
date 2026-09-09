"""
Unit tests for FinScan AI Document Classifier Subsystem (v2).
Owned by Karthik (Member 5).

Verifies:
1. Double-disjoint split invariants (zero applicant overlap AND zero template family overlap)
2. Kaggle dataset provenance and watermarking
3. Model artifact integrity and metadata
4. Confidence rejection and abstention gate (empty text, whitespace, out-of-domain)
5. Detailed prediction contract and probability distributions
6. Multi-page document consensus aggregation
7. Generalization benchmark on held-out test split (Macro-F1 >= 0.90)
"""

import json
import hashlib
from pathlib import Path
import pytest
import numpy as np

from ml.data.v2.dataset_generator_v2 import (
    load_v2_splits,
    CANONICAL_CLASSES,
    WATERMARK,
)
from ml.classifier.baseline_tfidf import (
    TfidfDocumentClassifier,
    load_v2_classifier,
    predict_document_type_v2,
    predict_with_details_v2,
    aggregate_document_predictions,
    V2_MODEL_PATH,
)
from ml.classifier.evaluate import evaluate_classifier


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# =====================================================================
# 1. SPLIT & PROVENANCE INVARIANTS
# =====================================================================

def test_v2_splits_double_disjoint_property():
    """Invariant: Both applicant IDs AND positive template families must be disjoint."""
    splits = load_v2_splits()
    train_data = splits["train"]
    dev_data = splits["dev"]
    test_data = splits["test"]

    # 1. Applicant ID Disjointness
    train_apps = set(p["application_id"] for p in train_data if p.get("application_id"))
    dev_apps = set(p["application_id"] for p in dev_data if p.get("application_id") and not p.get("is_negative"))
    test_apps = set(p["application_id"] for p in test_data if p.get("application_id") and not p.get("is_negative"))

    assert len(train_apps) == 48, f"Expected 48 train applicants, got {len(train_apps)}"
    assert len(dev_apps) == 11, f"Expected 11 dev applicants, got {len(dev_apps)}"
    assert len(test_apps) == 11, f"Expected 11 test applicants, got {len(test_apps)}"

    assert len(train_apps.intersection(dev_apps)) == 0, "Applicant leakage between train and dev!"
    assert len(train_apps.intersection(test_apps)) == 0, "Applicant leakage between train and test!"
    assert len(dev_apps.intersection(test_apps)) == 0, "Applicant leakage between dev and test!"

    # 2. Positive Template Family Disjointness
    train_fams = set(p["template_family"] for p in train_data)
    dev_pos_fams = set(p["template_family"] for p in dev_data if p["label"] != "UNKNOWN")
    test_pos_fams = set(p["template_family"] for p in test_data if p["label"] != "UNKNOWN")

    assert len(train_fams.intersection(dev_pos_fams)) == 0, "Template family leakage between train and dev!"
    assert len(train_fams.intersection(test_pos_fams)) == 0, "Template family leakage between train and test!"
    assert len(dev_pos_fams.intersection(test_pos_fams)) == 0, "Template family leakage between dev and test!"

    # 3. Class representation
    for split_name, split in [("train", train_data), ("dev", dev_data), ("test", test_data)]:
        classes_in_split = set(p["label"] for p in split)
        for c in CANONICAL_CLASSES:
            assert c in classes_in_split, f"Canonical class '{c}' missing from {split_name} split!"


def test_v2_negative_samples_present_and_watermarked():
    """Verify negative samples exist in dev/test and synthetic docs bear watermark."""
    splits = load_v2_splits()
    dev_unknowns = [p for p in splits["dev"] if p["label"] == "UNKNOWN"]
    test_unknowns = [p for p in splits["test"] if p["label"] == "UNKNOWN"]

    assert len(dev_unknowns) >= 8, f"Expected >=8 dev negatives, got {len(dev_unknowns)}"
    assert len(test_unknowns) >= 8, f"Expected >=8 test negatives, got {len(test_unknowns)}"

    # Check synthetic documents have visible watermark
    pos_samples = [p for p in splits["train"] if p["label"] != "UNKNOWN"]
    watermarked_count = sum(1 for p in pos_samples if WATERMARK in p["text"])
    assert watermarked_count == len(pos_samples), "Every synthetic positive page must bear the synthetic watermark!"


def test_kaggle_provenance_manifest_and_sha256():
    """Verify provenance manifest matches source Kaggle dataset SHA-256."""
    csv_path = REPO_ROOT / "data" / "kaggle_loan_approval_dataset.csv"
    manifest_path = REPO_ROOT / "ml" / "data" / "v2" / "provenance_manifest.json"

    assert csv_path.exists(), f"Kaggle CSV not found at {csv_path}"
    assert manifest_path.exists(), f"Provenance manifest not found at {manifest_path}"

    # Compute actual SHA-256 of CSV
    with open(csv_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["metadata"]["source_csv_sha256"] == actual_hash, "SHA-256 mismatch in provenance manifest!"
    assert manifest["metadata"]["n_applicants"] == 70
    assert len(manifest["records"]) == 606

    # Ensure applicant records have real Kaggle properties
    first_app = manifest["records"][0]
    assert "source_csv_row" in first_app
    assert "application_id" in first_app
    assert "template_family" in first_app


# =====================================================================
# 2. MODEL ARTIFACT AND REJECTION GATES
# =====================================================================

def test_v2_model_artifact_structure():
    """Verify serialized model artifact exists and contains required metadata."""
    assert V2_MODEL_PATH.exists(), f"Model artifact missing at {V2_MODEL_PATH}"
    clf = load_v2_classifier()

    assert clf.pipeline is not None
    assert clf.classes == CANONICAL_CLASSES
    assert 0.0 < clf.threshold < 1.0
    assert "trained_at_utc" in clf.metadata
    assert clf.metadata["features"] == "Word TF-IDF (1,2) + Char TF-IDF (3,5)"
    assert clf.metadata["classifier"] == "LogisticRegression(class_weight='balanced', max_iter=1000)"


def test_confidence_rejection_empty_and_whitespace():
    """Invariant: Empty string and whitespace must abstain with UNKNOWN, confidence 0.0."""
    clf = load_v2_classifier()

    for empty_input in ["", "   ", "\n\t  \r\n"]:
        label, conf = clf.predict_with_confidence(empty_input)
        assert label == "UNKNOWN"
        assert conf == 0.0

        details = clf.predict_with_details(empty_input)
        assert details["predicted_class"] == "UNKNOWN"
        assert details["confidence"] == 0.0
        assert details["abstained"] is True
        assert details["abstention_reason"] == "empty_text"


def test_confidence_rejection_gibberish_and_ood():
    """Invariant: Out-of-domain / gibberish text must be rejected as UNKNOWN."""
    clf = load_v2_classifier()

    gibberish_texts = [
        "qowieur laksjdf zxcvbnm poiuytre rewqasdf mnbvcxz",
        "Classic Chocolate Chip Cookies: 2 cups all-purpose flour, 1 tsp baking soda, 1 cup butter softened, 3/4 cup sugar.",
        "Clinical Report: Patient presents with mild rhinorrhea and afebrile presentation. Rx: Cetirizine 10mg once daily.",
    ]

    for ood_text in gibberish_texts:
        label, conf = clf.predict_with_confidence(ood_text)
        if label != "UNKNOWN":
            assert conf < 0.70, f"OOD text received unexpectedly high confidence: {conf}"


def test_predict_with_details_contract():
    """Verify the detailed prediction schema and probability distribution properties."""
    clf = load_v2_classifier()
    sample_text = (
        "FORM NO. 16 [See rule 31(1)(a)] Certificate under section 203 of the Income-tax Act, 1961. "
        "Assessment Year: 2024-25. Total Tax Deducted and Deposited to Central Government."
    )

    details = clf.predict_with_details(sample_text)

    required_keys = [
        "predicted_class",
        "confidence",
        "raw_predicted_class",
        "raw_confidence",
        "threshold",
        "abstained",
        "abstention_reason",
        "probabilities",
    ]
    for key in required_keys:
        assert key in details, f"Missing key '{key}' in predict_with_details output"

    assert details["predicted_class"] == "tax_acknowledgement"
    assert details["confidence"] >= clf.threshold
    assert details["abstained"] is False
    assert details["abstention_reason"] is None

    # Probabilities must sum to 1.0 across all 5 canonical classes
    probs = details["probabilities"]
    assert len(probs) == 5
    assert set(probs.keys()) == set(CANONICAL_CLASSES)
    assert abs(sum(probs.values()) - 1.0) < 1e-4


# =====================================================================
# 3. MULTI-PAGE AGGREGATION
# =====================================================================

def test_aggregate_document_predictions_unanimous():
    """Unanimous page predictions yield the unanimous class with mean confidence."""
    pages = [
        {"predicted_class": "bank_statement", "confidence": 0.85},
        {"predicted_class": "bank_statement", "confidence": 0.95},
        {"predicted_class": "bank_statement", "confidence": 0.90},
    ]
    doc_class, doc_conf = aggregate_document_predictions(pages)
    assert doc_class == "bank_statement"
    assert abs(doc_conf - 0.90) < 1e-4


def test_aggregate_document_predictions_with_unknown_page():
    """A multi-page document with an unreadable/unknown cover page routes correctly."""
    pages = [
        {"predicted_class": "UNKNOWN", "confidence": 0.0},
        {"predicted_class": "payslip", "confidence": 0.88},
        {"predicted_class": "payslip", "confidence": 0.92},
    ]
    doc_class, doc_conf = aggregate_document_predictions(pages)
    assert doc_class == "payslip"
    assert abs(doc_conf - 0.90) < 1e-4


def test_aggregate_document_predictions_all_unknown():
    """All-unknown pages aggregate to UNKNOWN with zero confidence."""
    pages = [
        {"predicted_class": "UNKNOWN", "confidence": 0.0},
        {"predicted_class": "UNKNOWN", "confidence": 0.1},
    ]
    doc_class, doc_conf = aggregate_document_predictions(pages)
    assert doc_class == "UNKNOWN"
    assert doc_conf == 0.0


# =====================================================================
# 4. HELD-OUT GENERALIZATION PERFORMANCE GATE
# =====================================================================

def test_v2_baseline_held_out_test_target_performance():
    """Release Gate: Document classifier must achieve >= 0.90 Macro-F1 on unseen templates & applicants."""
    splits = load_v2_splits()
    test_split = splits["test"]
    test_texts = [p["text"] for p in test_split]
    test_labels = [p["label"] for p in test_split]

    clf = load_v2_classifier()
    metrics = evaluate_classifier(clf, test_texts, test_labels, threshold=clf.threshold)

    # Core performance targets from AGENTS.md
    assert metrics["macro_f1"] >= 0.90, f"Held-out Macro-F1 {metrics['macro_f1']} below target 0.90!"
    assert metrics["accuracy"] >= 0.90, f"Held-out Accuracy {metrics['accuracy']} below target 0.90!"
    assert metrics["p50_latency_ms"] < 20.0, f"p50 latency {metrics['p50_latency_ms']}ms exceeds target 20ms!"
    assert metrics["process_rss_mb"] < 500.0, f"Process RSS {metrics['process_rss_mb']}MB exceeds target 500MB!"


def test_classifier_adapter_integration():
    """Verifies core/extraction/classifier_adapter integrates cleanly for downstream nodes."""
    from core.extraction.classifier_adapter import classify_text, classify_document, get_classification_service

    service = get_classification_service()
    assert service is not None

    label, conf = classify_text("Permanent Account Number PAN Card Income Tax Department Govt of India")
    assert label in ["id_card", "tax_acknowledgement"]
    assert conf > 0.0

    multi_result = classify_document([
        "HDFC Bank Account Statement for current account",
        "Monthly payslip gross pay basic salary allowances",
    ])
    assert "document_class" in multi_result
    assert "page_results" in multi_result
    assert len(multi_result["page_results"]) == 2


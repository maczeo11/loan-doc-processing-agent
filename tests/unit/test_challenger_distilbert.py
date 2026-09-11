"""
Tests for the DistilBERT challenger classifier (ml/classifier/
challenger_distilbert.py).

Skipped entirely when torch/transformers aren't installed (they're
deliberately absent from requirements-ci.txt - see that file's comment) -
this file exercises the real training/save/load round trip, which needs the
real runtime, not the sklearn/heuristic fallback path.
"""

import json
import os

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from ml.classifier.challenger_distilbert import DistilBertClassifier  # noqa: E402


# Tiny synthetic set - enough for one real forward/backward pass per class,
# not a quality bar. Keeps this test fast (batch_size=2, epochs=1).
_TRAIN_TEXTS = [
    "This is a loan application form. Applicant name: Jane Doe.",
    "Payslip for the month. Basic Salary: 50000. Net Pay: 45000.",
    "Bank statement. Opening balance 10000. Closing balance 12000.",
    "Income Tax Return ITR-V acknowledgement. Assessment Year 2024-25.",
]
_TRAIN_LABELS = ["application_form", "payslip", "bank_statement", "tax_acknowledgement"]


def test_save_does_not_clobber_huggingface_config(tmp_path):
    """
    Regression test: DistilBertClassifier.save() previously overwrote the
    real HF config.json (written by model.save_pretrained()) with a custom
    metadata dict, making every saved checkpoint fail to reload via
    AutoModelForSequenceClassification.from_pretrained() with a "does not
    recognize this architecture" error. The fix writes that metadata to a
    separate finscan_metadata.json instead.
    """
    save_dir = str(tmp_path / "distilbert_test")
    clf = DistilBertClassifier(model_path=save_dir, batch_size=2)
    clf.train(_TRAIN_TEXTS, _TRAIN_LABELS, epochs=1, batch_size=2)
    clf.save(save_dir)

    config_path = os.path.join(save_dir, "config.json")
    metadata_path = os.path.join(save_dir, "finscan_metadata.json")

    assert os.path.exists(config_path), "save_pretrained() should have written the real HF config.json"
    assert os.path.exists(metadata_path), "FinScan metadata should be in its own sidecar file"

    with open(config_path, encoding="utf-8") as f:
        hf_config = json.load(f)
    # The real HF config must survive - this is what from_pretrained() needs
    # to pick the right model class on reload.
    assert hf_config.get("model_type") == "distilbert"
    assert "architectures" in hf_config

    with open(metadata_path, encoding="utf-8") as f:
        finscan_metadata = json.load(f)
    assert finscan_metadata["model_type"] == "distilbert_sequence_classifier"
    assert finscan_metadata["classes"] == [
        "application_form",
        "payslip",
        "bank_statement",
        "tax_acknowledgement",
        "id_card",
    ]


def test_save_then_load_round_trip_predicts_without_error(tmp_path):
    """
    The actual bug symptom: a fresh DistilBertClassifier instance pointed at
    a saved checkpoint must be able to load() and predict_with_confidence()
    without hitting the "does not recognize this architecture" error.
    """
    save_dir = str(tmp_path / "distilbert_roundtrip")
    trainer = DistilBertClassifier(model_path=save_dir, batch_size=2)
    trainer.train(_TRAIN_TEXTS, _TRAIN_LABELS, epochs=1, batch_size=2)
    trainer.save(save_dir)

    reloaded = DistilBertClassifier(model_path=save_dir)
    reloaded.load(save_dir)

    assert reloaded.model is not None
    assert reloaded.tokenizer is not None

    label, confidence = reloaded.predict_with_confidence("Payslip. Net Pay: 40000.")
    assert label in {
        "application_form",
        "payslip",
        "bank_statement",
        "tax_acknowledgement",
        "id_card",
    }
    assert 0.0 <= confidence <= 1.0

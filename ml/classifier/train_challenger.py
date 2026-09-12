"""
Training pipeline for FinScan AI Document Classifier Challenger (DistilBERT).
Owned by Member 5 (Karthik).

Mirrors ml/classifier/train.py's structure (same data split, same MLflow
logging conventions) but trains DistilBertClassifier (ml/classifier/
challenger_distilbert.py) instead of the TF-IDF baseline, serializing to
ml/artifacts/distilbert/.

No standalone training script existed for the challenger before this - only
the DistilBertClassifier.train() method itself, which already enforces the
AGENTS.md constraints (epochs<=3, batch 2-4, AdamW lr=2e-5, seq_len=256).
"""

import os
from typing import Any, Dict, Optional

try:
    import mlflow
except ImportError:
    from ml.classifier import mlflow_compat as mlflow

from ml.classifier.challenger_distilbert import DOCUMENT_CLASSES, DistilBertClassifier
from ml.data.v2.dataset_generator_v2 import load_v2_splits


def train_and_log_challenger(
    splits_path: Optional[str] = None,
    save_path: str = "ml/artifacts/distilbert",
    experiment_name: str = "finscan-classifier",
    epochs: int = 3,
    lr: float = 2e-5,
    batch_size: int = 4,
) -> Dict[str, Any]:
    """
    Executes training for the DistilBERT challenger, wrapped in an MLflow run,
    mirroring train_and_log_baseline()'s structure for like-for-like tracking.
    """
    splits = load_v2_splits(splits_path) if splits_path else load_v2_splits()
    train_split = splits["train"]
    # DistilBertClassifier only knows the 5 canonical classes (no UNKNOWN) -
    # the negative/OOD samples that seed UNKNOWN in the baseline's dev/test
    # splits have no place in this classifier's label space, so skip them.
    train_texts = [p["text"] for p in train_split if p["label"] in DOCUMENT_CLASSES]
    train_labels = [p["label"] for p in train_split if p["label"] in DOCUMENT_CLASSES]

    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="train_challenger_distilbert"):
        mlflow.log_params(
            {
                "model_type": "DistilBERT sequence classifier",
                "base_model": "distilbert-base-uncased",
                "epochs": epochs,
                "lr": lr,
                "batch_size": batch_size,
                "max_seq_len": 256,
                "train_samples": len(train_texts),
                "canonical_classes": ",".join(DOCUMENT_CLASSES),
                "output_artifact": save_path,
            }
        )

        clf = DistilBertClassifier(model_path=save_path, batch_size=batch_size)
        train_result = clf.train(train_texts, train_labels, epochs=epochs, lr=lr, batch_size=batch_size)
        clf.save(save_path)

        mlflow.log_metric("train_sample_count", float(len(train_texts)))
        mlflow.log_metric("final_train_loss", train_result.get("loss", 0.0))
        mlflow.log_param("used_real_torch_runtime", clf.is_torch_available)
        if os.path.exists(save_path):
            artifact_size_mb = sum(
                os.path.getsize(os.path.join(save_path, f))
                for f in os.listdir(save_path)
                if os.path.isfile(os.path.join(save_path, f))
            ) / (1024.0 * 1024.0)
            mlflow.log_metric("model_size_mb", round(artifact_size_mb, 2))

        print(f"Challenger DistilBERT trained on {len(train_texts)} samples (torch runtime: {clf.is_torch_available}).")
        print(f"Model artifact saved to: {save_path}")

        return {
            "train_samples": len(train_texts),
            "save_path": save_path,
            "used_real_torch_runtime": clf.is_torch_available,
            "train_result": train_result,
        }


if __name__ == "__main__":
    train_and_log_challenger()

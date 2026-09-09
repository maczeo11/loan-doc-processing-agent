"""
Training pipeline for FinScan AI Document Classifier Baseline.
Owned by Member 5 (Karthik).

Trains TF-IDF word+char feature extraction with balanced Logistic Regression,
serializes the model artifact to ml/artifacts/v2/baseline_tfidf.joblib, and logs
all parameters, metrics, and artifacts to MLflow.
"""

import os
from typing import Dict, Any, Optional

try:
    import mlflow
except ImportError:
    from ml.classifier import mlflow_compat as mlflow

from ml.classifier.baseline_tfidf import (
    train_baseline_classifier,
    DEFAULT_MODEL_PATH,
    CANONICAL_CLASSES,
)
from ml.data.v2.dataset_generator_v2 import load_v2_splits


def train_and_log_baseline(
    splits_path: Optional[str] = None,
    save_path: str = DEFAULT_MODEL_PATH,
    experiment_name: str = "finscan-classifier"
) -> Dict[str, Any]:
    """
    Executes training for baseline document classifier wrapped in an MLflow run.
    """
    splits = load_v2_splits(splits_path) if splits_path else load_v2_splits()
    train_split = splits["train"]
    train_texts = [p["text"] for p in train_split]
    train_labels = [p["label"] for p in train_split]

    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name="train_baseline_tfidf"):
        # Log parameters
        mlflow.log_params({
            "model_type": "TF-IDF + Logistic Regression",
            "classifier": "LogisticRegression",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "max_iter": 1000,
            "word_ngram_range": "(1, 2)",
            "char_ngram_range": "(3, 5)",
            "max_features_word": 12000,
            "max_features_char": 25000,
            "train_samples": len(train_texts),
            "canonical_classes": ",".join(CANONICAL_CLASSES),
            "output_artifact": save_path,
        })

        # Train pipeline
        pipeline = train_baseline_classifier(train_texts, train_labels, save_path=save_path)

        # Log metrics & artifacts
        mlflow.log_metric("train_sample_count", float(len(train_texts)))
        if os.path.exists(save_path):
            mlflow.log_artifact(save_path, artifact_path="model")
            artifact_size_mb = os.path.getsize(save_path) / (1024.0 * 1024.0)
            mlflow.log_metric("model_size_mb", round(artifact_size_mb, 2))

        print(f"Baseline TF-IDF trained successfully on {len(train_texts)} samples.")
        print(f"Model artifact saved to: {save_path}")

        return {
            "train_samples": len(train_texts),
            "save_path": save_path,
            "pipeline": pipeline,
        }


if __name__ == "__main__":
    train_and_log_baseline()

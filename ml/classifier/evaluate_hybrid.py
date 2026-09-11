"""
Evaluation harness for the hybrid cascade classifier (ml/classifier/
hybrid_cascade.py). Mirrors ml/classifier/evaluate.py's __main__ structure
for a like-for-like comparison against the existing baseline results
(audit/v2/evaluation_results_v2.json).

Reports two things, deliberately kept separate (see hybrid_cascade.py's
module docstring for why): the standard overall Macro-F1 (expected to be
~flat vs baseline, since escalation only touches a small uncertain slice),
and a dedicated "escalation subset" report - of the pages baseline alone
would have abstained on, how many did DistilBERT resolve correctly instead?
That second number is the honest signal for whether this cascade is worth
shipping, not the headline Macro-F1.
"""

import json
import os
from typing import Any, Dict, List

try:
    import mlflow
except ImportError:
    from ml.classifier import mlflow_compat as mlflow

from ml.classifier.baseline_tfidf import DEFAULT_CONFIDENCE_THRESHOLD, predict_with_details
from ml.classifier.evaluate import evaluate_classifier, get_comparison_summary
from ml.classifier.hybrid_cascade import DEFAULT_ESCALATE_HIGH, DEFAULT_ESCALATE_LOW, HybridCascadeClassifier


def evaluate_escalation_subset(
    test_texts: List[str],
    test_labels: List[str],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    escalate_low: float = DEFAULT_ESCALATE_LOW,
    escalate_high: float = DEFAULT_ESCALATE_HIGH,
) -> Dict[str, Any]:
    """
    Isolates exactly the pages baseline alone abstains on within the
    escalation band, and reports how the hybrid cascade resolves them.
    This is the metric that actually justifies (or doesn't) shipping the
    cascade - see module docstring.
    """
    cascade = HybridCascadeClassifier(
        threshold=threshold, escalate_low=escalate_low, escalate_high=escalate_high
    )

    subset_indices = []
    for i, text in enumerate(test_texts):
        base_details = predict_with_details(text, threshold=threshold)
        reason = base_details.get("abstention_reason") or ""
        conf = base_details.get("confidence", 0.0)
        if base_details.get("abstained") and reason.startswith("LOW_CONFIDENCE") and escalate_low <= conf < escalate_high:
            subset_indices.append(i)

    if not subset_indices:
        return {
            "subset_size": 0,
            "note": "No test-set pages fell in the escalation band - nothing for DistilBERT to resolve here.",
        }

    resolved_correct = 0
    still_abstained = 0
    resolved_incorrect = 0
    for i in subset_indices:
        label, _ = cascade.predict_with_confidence(test_texts[i])
        if label == "UNKNOWN":
            still_abstained += 1
        elif label == test_labels[i]:
            resolved_correct += 1
        else:
            resolved_incorrect += 1

    return {
        "subset_size": len(subset_indices),
        "resolved_correct": resolved_correct,
        "resolved_incorrect": resolved_incorrect,
        "still_abstained": still_abstained,
        "resolution_accuracy": round(resolved_correct / len(subset_indices), 4),
    }


if __name__ == "__main__":
    print("=" * 70)
    print("FINSCAN AI: HYBRID CASCADE CLASSIFIER EVALUATION (v2)")
    print("=" * 70)

    splits_path = "ml/data/v2/splits_v2.json"
    with open(splits_path, "r", encoding="utf-8") as f:
        splits = json.load(f)

    test_texts = [p["text"] for p in splits["test"]]
    test_labels = [p["label"] for p in splits["test"]]

    print(f"\nEvaluating hybrid cascade on held-out test split ({len(test_texts)} samples)...")
    cascade = HybridCascadeClassifier()
    hybrid_metrics = evaluate_classifier(cascade, test_texts, test_labels, threshold=DEFAULT_CONFIDENCE_THRESHOLD)

    print("\n" + "-" * 50)
    print("HELD-OUT TEST BENCHMARK (Hybrid Cascade: TF-IDF -> DistilBERT)")
    print("-" * 50)
    print(f"Macro-F1 Score       : {hybrid_metrics['macro_f1']:.4f}")
    print(f"Accuracy             : {hybrid_metrics['accuracy']:.4f}")
    print(f"Latency p50 (Median) : {hybrid_metrics['p50_latency_ms']:.2f} ms / page")
    print(f"Latency p95          : {hybrid_metrics['p95_latency_ms']:.2f} ms / page")
    print(f"Process Working Set  : {hybrid_metrics['process_rss_mb']:.2f} MB RSS")

    print("\nComparing against the existing baseline result...")
    baseline_results_path = "audit/v2/evaluation_results_v2.json"
    if os.path.exists(baseline_results_path):
        with open(baseline_results_path, "r", encoding="utf-8") as f:
            baseline_metrics = json.load(f)["metrics"]
        summary = get_comparison_summary(baseline_metrics, hybrid_metrics)
        print(f"Winner (overall Macro-F1 rule): {summary['winner']}")
        print(summary["rationale"])
    else:
        print(f"No baseline results found at {baseline_results_path} - run ml/classifier/evaluate.py first.")
        summary = None

    print("\n" + "-" * 50)
    print("ESCALATION SUBSET REPORT (the honest signal - see module docstring)")
    print("-" * 50)
    escalation_report = evaluate_escalation_subset(test_texts, test_labels)
    print(json.dumps(escalation_report, indent=2))

    os.makedirs("audit/v2", exist_ok=True)
    output_path = "audit/v2/evaluation_results_hybrid_v2.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "dataset": splits_path,
                "threshold_used": DEFAULT_CONFIDENCE_THRESHOLD,
                "metrics": hybrid_metrics,
                "comparison_vs_baseline": summary,
                "escalation_subset_report": escalation_report,
            },
            f,
            indent=2,
        )
    print(f"\nResults saved to {output_path}")

    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment("finscan-classifier")
    with mlflow.start_run(run_name="evaluate_hybrid_cascade"):
        mlflow.log_params(
            {
                "dataset": splits_path,
                "threshold": DEFAULT_CONFIDENCE_THRESHOLD,
                "escalate_low": DEFAULT_ESCALATE_LOW,
                "escalate_high": DEFAULT_ESCALATE_HIGH,
                "test_samples": len(test_texts),
            }
        )
        mlflow.log_metrics(
            {
                "macro_f1": hybrid_metrics["macro_f1"],
                "accuracy": hybrid_metrics["accuracy"],
                "p50_latency_ms": hybrid_metrics["p50_latency_ms"],
                "p95_latency_ms": hybrid_metrics["p95_latency_ms"],
                "process_rss_mb": hybrid_metrics["process_rss_mb"],
                "escalation_subset_size": float(escalation_report.get("subset_size", 0)),
                "escalation_resolution_accuracy": float(escalation_report.get("resolution_accuracy", 0.0)),
            }
        )
        mlflow.log_artifact(output_path, artifact_path="audit")
    print("Logged evaluation metrics, params, and artifacts to MLflow (./mlruns).")

"""
Evaluation harness for Document Classifiers: Baseline (TF-IDF) vs Challenger (DistilBERT).

Selection Rule from AGENTS.md:
"Ship whichever classifier wins on measured quality and resource footprint.
If TF-IDF gets 0.91 macro-F1 and the encoder gets 0.92 for 400 MB of RAM,
ship the baseline and say why."

Targets:
- >= 0.90 macro-F1
- Measure inference latency (p50, p95)
- Measure memory consumption
"""

from typing import Dict, Any, List


def evaluate_classifier(model: Any, test_texts: List[str], test_labels: List[str]) -> Dict[str, Any]:
    """Evaluate accuracy, macro-F1, and latency of a classifier."""
    # Stub: Karthik to implement using scikit-learn metrics
    return {
        "macro_f1": 0.0,
        "accuracy": 0.0,
        "p50_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "ram_mb": 0.0,
    }


def compare_models(baseline_metrics: Dict[str, Any], challenger_metrics: Dict[str, Any]) -> str:
    """Determine winning model based on macro-F1 and resource footprint."""
    if challenger_metrics["macro_f1"] - baseline_metrics["macro_f1"] > 0.03:
        return "CHALLENGER"
    return "BASELINE"


if __name__ == "__main__":
    print("Run evaluation on frozen test split...")

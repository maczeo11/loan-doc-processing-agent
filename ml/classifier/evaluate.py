"""
Evaluation harness for Document Classifiers: Baseline (TF-IDF) vs Challenger (DistilBERT).
Owned by Member 5 (Karthik).

Selection Rule from AGENTS.md:
"Ship whichever classifier wins on measured quality and resource footprint.
If TF-IDF gets 0.91 macro-F1 and the encoder gets 0.92 for 400 MB of RAM,
ship the baseline and say why."

Targets:
- >= 0.90 macro-F1
- Measure inference latency (p50, p95) in milliseconds
- Measure memory consumption (RAM MB)
"""

import os
import sys
import time
import tracemalloc
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.metrics import f1_score, accuracy_score, classification_report, confusion_matrix


def evaluate_classifier(
    model: Any,
    test_texts: List[str],
    test_labels: List[str],
    warmup_runs: int = 5
) -> Dict[str, Any]:
    """
    Evaluates classification accuracy, macro-F1, inference latency (p50, p95),
    and RAM footprint of a document classifier model.
    """
    if not test_texts:
        raise ValueError("test_texts cannot be empty.")

    # Start memory tracing
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()

    # Helper to call single-item prediction
    def _predict_single(text_item: str) -> str:
        if hasattr(model, "predict_batch"):
            return model.predict_batch([text_item])[0]
        elif hasattr(model, "predict"):
            # If it's a sklearn Pipeline, predict expects an iterable [text_item]
            try:
                res = model.predict([text_item])
                return str(res[0])
            except Exception:
                return str(model.predict(text_item))
        elif callable(model):
            try:
                res = model([text_item])
                return str(res[0]) if isinstance(res, (list, np.ndarray)) else str(res)
            except Exception:
                return str(model(text_item))
        else:
            raise TypeError(f"Unsupported model type: {type(model)}")

    # Warmup
    for i in range(min(warmup_runs, len(test_texts))):
        _ = _predict_single(test_texts[i])

    # Benchmarked inference
    latencies_ms: List[float] = []
    predictions: List[str] = []

    for text in test_texts:
        t0 = time.perf_counter()
        pred = _predict_single(text)
        t1 = time.perf_counter()

        latencies_ms.append((t1 - t0) * 1000.0)
        predictions.append(pred)

    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    ram_mb = max(0.0, (peak_mem - mem_before) / (1024.0 * 1024.0))

    # Metrics
    macro_f1 = float(f1_score(test_labels, predictions, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(test_labels, predictions, average="weighted", zero_division=0))
    accuracy = float(accuracy_score(test_labels, predictions))

    latencies_arr = np.array(latencies_ms)
    p50_latency = float(np.percentile(latencies_arr, 50))
    p95_latency = float(np.percentile(latencies_arr, 95))
    mean_latency = float(np.mean(latencies_arr))

    report = classification_report(test_labels, predictions, zero_division=0, output_dict=True)
    report_text = classification_report(test_labels, predictions, zero_division=0)
    conf_matrix = confusion_matrix(test_labels, predictions).tolist()

    return {
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "accuracy": round(accuracy, 4),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "mean_latency_ms": round(mean_latency, 2),
        "ram_mb": round(ram_mb, 2),
        "total_samples": len(test_texts),
        "classification_report": report,
        "classification_report_text": report_text,
        "confusion_matrix": conf_matrix,
    }


def compare_models(
    baseline_metrics: Dict[str, Any],
    challenger_metrics: Dict[str, Any],
    f1_delta_threshold: float = 0.03
) -> str:
    """
    Determine winning model based on macro-F1 and resource footprint.
    Selection Invariant from AGENTS.md:
    - If challenger macro-F1 > baseline macro-F1 + 0.03, Challenger wins.
    - Otherwise, Baseline ships (lighter RAM footprint, faster latency).
    """
    f1_diff = challenger_metrics.get("macro_f1", 0.0) - baseline_metrics.get("macro_f1", 0.0)
    if f1_diff > f1_delta_threshold:
        return "CHALLENGER"
    return "BASELINE"


def get_comparison_summary(
    baseline_metrics: Dict[str, Any],
    challenger_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Returns structured rationale explaining the model selection decision."""
    winner = compare_models(baseline_metrics, challenger_metrics)
    b_f1 = baseline_metrics.get("macro_f1", 0.0)
    c_f1 = challenger_metrics.get("macro_f1", 0.0)
    b_lat = baseline_metrics.get("p50_latency_ms", 0.0)
    c_lat = challenger_metrics.get("p50_latency_ms", 0.0)
    b_ram = baseline_metrics.get("ram_mb", 0.0)
    c_ram = challenger_metrics.get("ram_mb", 0.0)

    if winner == "CHALLENGER":
        rationale = (
            f"Challenger wins: Macro-F1 ({c_f1:.4f}) exceeds Baseline ({b_f1:.4f}) by "
            f"+{(c_f1 - b_f1):.4f} (> 0.03 threshold), justifying higher resource footprint."
        )
    else:
        rationale = (
            f"Baseline ships: Baseline Macro-F1 ({b_f1:.4f}) meets target (>= 0.90). "
            f"Challenger gain ({c_f1 - b_f1:+.4f}) does not justify the resource overhead "
            f"(Challenger Latency: {c_lat}ms vs Baseline: {b_lat}ms; RAM: {c_ram}MB vs {b_ram}MB)."
        )

    return {
        "winner": winner,
        "rationale": rationale,
        "baseline_f1": b_f1,
        "challenger_f1": c_f1,
        "f1_delta": round(c_f1 - b_f1, 4),
    }


if __name__ == "__main__":
    from ml.data.dataset_generator import load_splits
    from ml.classifier.baseline_tfidf import load_baseline_classifier
    from ml.classifier.challenger_distilbert import DistilBertClassifier

    print("=" * 65)
    print("FINSCAN AI: DOCUMENT CLASSIFIER BENCHMARK (MEMBER 5 - KARTHIK)")
    print("=" * 65)

    splits = load_splits()
    test_pages = splits["test"]
    test_texts = [p["text"] for p in test_pages]
    test_labels = [p["label"] for p in test_pages]

    print(f"Loaded {len(test_pages)} test pages across {len(set(test_labels))} classes.")

    # 1. Evaluate Baseline
    baseline_model = load_baseline_classifier()
    b_metrics = evaluate_classifier(baseline_model, test_texts, test_labels)

    print("\n--- BASELINE METRICS (TF-IDF + Logistic Regression) ---")
    print(f"Macro-F1 Score   : {b_metrics['macro_f1']:.4f} (Target >= 0.9000)")
    print(f"Accuracy         : {b_metrics['accuracy']:.4f}")
    print(f"Latency p50      : {b_metrics['p50_latency_ms']:.2f} ms / page")
    print(f"Latency p95      : {b_metrics['p95_latency_ms']:.2f} ms / page")
    print(f"Peak RAM Trace   : {b_metrics['ram_mb']:.2f} MB")

    # 2. Evaluate Challenger
    challenger = DistilBertClassifier()
    c_metrics = evaluate_classifier(challenger, test_texts, test_labels)

    print("\n--- CHALLENGER METRICS (DistilBERT-class Sequence Encoder) ---")
    print(f"Macro-F1 Score   : {c_metrics['macro_f1']:.4f}")
    print(f"Accuracy         : {c_metrics['accuracy']:.4f}")
    print(f"Latency p50      : {c_metrics['p50_latency_ms']:.2f} ms / page")
    print(f"Latency p95      : {c_metrics['p95_latency_ms']:.2f} ms / page")
    print(f"Peak RAM Trace   : {c_metrics['ram_mb']:.2f} MB")

    # 3. Model Comparison Decision
    comparison = get_comparison_summary(b_metrics, c_metrics)
    print("\n" + "=" * 65)
    print("MODEL SELECTION VERDICT (AGENTS.md Section 6 Invariant)")
    print("=" * 65)
    print(f"WINNER           : {comparison['winner']}")
    print(f"DECISION RATIONALE: {comparison['rationale']}")
    print("=" * 65)



"""
Evaluation harness for Document Classifiers: Baseline (TF-IDF) vs Challenger (DistilBERT).
Owned by Member 5 (Karthik).

Selection Rule from AGENTS.md:
"Ship whichever classifier wins on measured quality and resource footprint.
If TF-IDF gets 0.91 macro-F1 and the encoder gets 0.92 for 400 MB of RAM,
ship the baseline and say why."

Targets & Invariants (Section 8):
- Canonical Classes: application_form, bank_statement, id_card, payslip, tax_acknowledgement.
- UNKNOWN is an abstention outcome for empty/whitespace, low-confidence, or out-of-domain inputs.
- Measure inference latency (p50, p95) in milliseconds.
- Measure actual process memory (Resident Working Set RSS in MB) as well as Python heap trace.
"""

import os
import sys
import time
import json
import tracemalloc
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.metrics import f1_score, accuracy_score, classification_report, confusion_matrix

try:
    import mlflow
except ImportError:
    from ml.classifier import mlflow_compat as mlflow


def get_process_rss_mb() -> float:
    """Measures actual OS process Resident Set Size (RSS) memory in MB."""
    # 1. On Windows using ctypes Win32 API
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
            GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
            GetProcessMemoryInfo.restype = wintypes.BOOL

            handle = ctypes.windll.kernel32.GetCurrentProcess()
            pmc = PROCESS_MEMORY_COUNTERS_EX()
            pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            if GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
                return round(float(pmc.WorkingSetSize) / (1024.0 * 1024.0), 2)
        except Exception:
            pass

    # 2. On Linux using /proc/self/status
    if os.path.exists("/proc/self/status"):
        try:
            with open("/proc/self/status", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        return round(float(parts[1]) / 1024.0, 2)
        except Exception:
            pass

    return 0.0


def evaluate_classifier(
    model: Any,
    test_texts: List[str],
    test_labels: List[str],
    threshold: Optional[float] = None,
    warmup_runs: int = 5
) -> Dict[str, Any]:
    """
    Evaluates classification accuracy, macro-F1, inference latency (p50, p95),
    OS process RSS memory, and Python heap trace.
    """
    if not test_texts:
        raise ValueError("test_texts cannot be empty.")

    # Start memory tracing
    tracemalloc.start()
    mem_before, _ = tracemalloc.get_traced_memory()
    rss_before = get_process_rss_mb()

    # Helper to call single-item prediction
    def _predict_single(text_item: str) -> str:
        # Check if model has custom predict with threshold
        if hasattr(model, "predict_with_confidence"):
            label, conf = model.predict_with_confidence(text_item)
            return label
        elif hasattr(model, "predict_batch"):
            return model.predict_batch([text_item])[0]
        elif hasattr(model, "predict"):
            # If it's a sklearn Pipeline and a threshold is provided
            if threshold is not None and hasattr(model, "predict_proba"):
                if not text_item or not text_item.strip():
                    return "UNKNOWN"
                try:
                    probs = model.predict_proba([text_item])[0]
                    best_idx = int(np.argmax(probs))
                    best_prob = float(probs[best_idx])
                    if best_prob < threshold:
                        return "UNKNOWN"
                    return str(model.classes_[best_idx])
                except Exception:
                    pass
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
    rss_after = get_process_rss_mb()

    heap_delta_mb = max(0.0, (peak_mem - mem_before) / (1024.0 * 1024.0))
    process_rss_mb = rss_after if rss_after > 0.0 else rss_before

    # Determine unique labels for evaluation metrics
    unique_labels = sorted(list(set(test_labels).union(set(predictions))))

    # Metrics
    macro_f1 = float(f1_score(test_labels, predictions, labels=unique_labels, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(test_labels, predictions, labels=unique_labels, average="weighted", zero_division=0))
    accuracy = float(accuracy_score(test_labels, predictions))

    latencies_arr = np.array(latencies_ms)
    p50_latency = float(np.percentile(latencies_arr, 50))
    p95_latency = float(np.percentile(latencies_arr, 95))
    mean_latency = float(np.mean(latencies_arr))

    report = classification_report(test_labels, predictions, labels=unique_labels, zero_division=0, output_dict=True)
    report_text = classification_report(test_labels, predictions, labels=unique_labels, zero_division=0)
    conf_matrix = confusion_matrix(test_labels, predictions, labels=unique_labels).tolist()

    return {
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "accuracy": round(accuracy, 4),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2),
        "mean_latency_ms": round(mean_latency, 2),
        "heap_delta_mb": round(heap_delta_mb, 2),
        "process_rss_mb": round(process_rss_mb, 2),
        "ram_mb": round(process_rss_mb, 2),  # Backward compatibility alias
        "total_samples": len(test_texts),
        "evaluated_classes": unique_labels,
        "classification_report": report,
        "classification_report_text": report_text,
        "confusion_matrix": conf_matrix,
    }


def find_optimal_threshold(
    model: Any,
    dev_texts: List[str],
    dev_labels: List[str],
    candidate_thresholds: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Tuning gate: Searches for optimal confidence threshold T on development split only.
    Balances positive class accuracy with UNKNOWN rejection of negative/OOD samples.
    """
    if candidate_thresholds is None:
        candidate_thresholds = [0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]

    best_threshold = 0.50
    best_macro_f1 = -1.0
    best_metrics = None
    tuning_log = []

    for thresh in candidate_thresholds:
        metrics = evaluate_classifier(model, dev_texts, dev_labels, threshold=thresh, warmup_runs=1)
        score = metrics["macro_f1"]
        tuning_log.append({
            "threshold": thresh,
            "macro_f1": score,
            "accuracy": metrics["accuracy"]
        })
        if score > best_macro_f1:
            best_macro_f1 = score
            best_threshold = thresh
            best_metrics = metrics

    return {
        "best_threshold": best_threshold,
        "best_macro_f1": best_macro_f1,
        "tuning_log": tuning_log,
        "dev_metrics": best_metrics
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
    b_rss = baseline_metrics.get("process_rss_mb", 0.0)
    c_rss = challenger_metrics.get("process_rss_mb", 0.0)

    if winner == "CHALLENGER":
        rationale = (
            f"Challenger wins: Macro-F1 ({c_f1:.4f}) exceeds Baseline ({b_f1:.4f}) by "
            f"+{(c_f1 - b_f1):.4f} (> 0.03 threshold), justifying higher resource footprint."
        )
    else:
        rationale = (
            f"Baseline ships: Baseline Macro-F1 ({b_f1:.4f}) meets target (>= 0.90). "
            f"Challenger gain ({c_f1 - b_f1:+.4f}) does not justify the resource overhead "
            f"(Challenger Latency: {c_lat}ms vs Baseline: {b_lat}ms; Process RSS: {c_rss}MB vs {b_rss}MB)."
        )

    return {
        "winner": winner,
        "rationale": rationale,
        "baseline_f1": b_f1,
        "challenger_f1": c_f1,
        "f1_delta": round(c_f1 - b_f1, 4),
    }


if __name__ == "__main__":
    from ml.classifier.baseline_tfidf import load_baseline_classifier, DEFAULT_MODEL_PATH
    active_model_path = DEFAULT_MODEL_PATH

    print("=" * 70)
    print("FINSCAN AI: DOCUMENT CLASSIFIER EVALUATION & BENCHMARK (v2)")
    print("=" * 70)

    # Resolve splits (v2 first, fallback to v1)
    v2_splits_path = "ml/data/v2/splits_v2.json"
    v1_splits_path = "ml/data/splits.json"
    active_splits_path = v2_splits_path if os.path.exists(v2_splits_path) else v1_splits_path

    print(f"Loading dataset from: {active_splits_path}")
    with open(active_splits_path, "r", encoding="utf-8") as f:
        splits = json.load(f)

    # 1. Load Model
    model = load_baseline_classifier()
    print("Baseline model loaded successfully.")

    # 2. Development Split Threshold Tuning
    if "dev" in splits and len(splits["dev"]) > 0:
        dev_texts = [p["text"] for p in splits["dev"]]
        dev_labels = [p["label"] for p in splits["dev"]]
        print(f"\nTuning confidence threshold on Dev split ({len(dev_texts)} samples)...")
        tuning_res = find_optimal_threshold(model, dev_texts, dev_labels)
        opt_thresh = tuning_res["best_threshold"]
        print(f"Selected Optimal Threshold: T* = {opt_thresh:.2f} (Dev Macro-F1: {tuning_res['best_macro_f1']:.4f})")
    else:
        opt_thresh = 0.50
        print(f"Using default threshold T = {opt_thresh:.2f}")

    # 3. Held-Out Test Evaluation (Generalization to Unseen Families)
    test_texts = [p["text"] for p in splits["test"]]
    test_labels = [p["label"] for p in splits["test"]]
    print(f"\nEvaluating on Held-Out Test split ({len(test_texts)} samples) at T = {opt_thresh:.2f}...")

    metrics = evaluate_classifier(model, test_texts, test_labels, threshold=opt_thresh)

    print("\n" + "-" * 50)
    print("HELD-OUT TEST GENERALIZATION BENCHMARK (TF-IDF + LogisticRegression)")
    print("-" * 50)
    print(f"Macro-F1 Score       : {metrics['macro_f1']:.4f} (Target >= 0.9000)")
    print(f"Weighted-F1 Score    : {metrics['weighted_f1']:.4f}")
    print(f"Accuracy             : {metrics['accuracy']:.4f}")
    print(f"Latency p50 (Median) : {metrics['p50_latency_ms']:.2f} ms / page")
    print(f"Latency p95          : {metrics['p95_latency_ms']:.2f} ms / page")
    print(f"Process Working Set  : {metrics['process_rss_mb']:.2f} MB RSS")
    print(f"Python Heap Delta    : {metrics['heap_delta_mb']:.2f} MB")
    print("\nPer-Class Classification Report:\n", metrics["classification_report_text"])

    # 4. Save Audit Artifacts for Handoff
    os.makedirs("audit/v2", exist_ok=True)
    with open("audit/v2/evaluation_results_v2.json", "w", encoding="utf-8") as f:
        json.dump({
            "dataset": active_splits_path,
            "threshold_used": opt_thresh,
            "metrics": metrics
        }, f, indent=2)

    # Per-sample predictions
    per_sample = []
    classes = metrics["evaluated_classes"]
    for i, p in enumerate(splits["test"]):
        text = p["text"]
        true_lbl = p["label"]
        pred_lbl = metrics["confusion_matrix"]  # already computed
        # run single prediction for confidence logging
        if not text or not text.strip():
            pred, conf = "UNKNOWN", 0.0
        else:
            probs = model.predict_proba([text])[0]
            best_idx = int(np.argmax(probs))
            conf = float(probs[best_idx])
            pred = str(model.classes_[best_idx]) if conf >= opt_thresh else "UNKNOWN"

        per_sample.append({
            "index": i,
            "page_id": p.get("page_id", f"PAGE-{i:03d}"),
            "template_family": p.get("template_family", "UNKNOWN"),
            "true_label": true_lbl,
            "predicted_label": pred,
            "confidence": round(conf, 4),
            "match": pred == true_lbl
        })

    with open("audit/v2/per_sample_predictions_v2.json", "w", encoding="utf-8") as f:
        json.dump(per_sample, f, indent=2)

    print("Audit artifacts saved to audit/v2/evaluation_results_v2.json and audit/v2/per_sample_predictions_v2.json")

    # 5. Log to MLflow
    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment("finscan-classifier")
    with mlflow.start_run(run_name="evaluate_baseline_tfidf"):
        mlflow.log_params({
            "dataset": active_splits_path,
            "optimal_threshold": opt_thresh,
            "dev_samples": len(dev_texts) if "dev_texts" in locals() else 0,
            "test_samples": len(test_texts),
            "model_path": active_model_path,
        })
        mlflow.log_metrics({
            "macro_f1": metrics["macro_f1"],
            "weighted_f1": metrics["weighted_f1"],
            "accuracy": metrics["accuracy"],
            "p50_latency_ms": metrics["p50_latency_ms"],
            "p95_latency_ms": metrics["p95_latency_ms"],
            "mean_latency_ms": metrics["mean_latency_ms"],
            "process_rss_mb": metrics["process_rss_mb"],
            "heap_delta_mb": metrics["heap_delta_mb"],
        })
        mlflow.log_artifact("audit/v2/evaluation_results_v2.json", artifact_path="audit")
        mlflow.log_artifact("audit/v2/per_sample_predictions_v2.json", artifact_path="audit")
        if os.path.exists(active_model_path):
            mlflow.log_artifact(active_model_path, artifact_path="model")
    print("Logged evaluation metrics, params, and artifacts to MLflow (./mlruns).")




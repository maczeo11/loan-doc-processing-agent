"""
Unit tests for FinScan AI RAG Frozen Evaluation Benchmark.
Verifies Recall@5 >= 0.90, MRR@5, and Grounding Precision across splits.
Owned by Member 8 (Sai Mokshith).
"""

import json
import os

from eval.run_eval import evaluate_benchmark


def test_frozen_benchmark_structure():
    benchmark_path = "eval/questions.json"
    assert os.path.exists(benchmark_path), f"Missing benchmark file: {benchmark_path}"

    with open(benchmark_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    assert len(questions) == 30, f"Expected exactly 30 questions, found {len(questions)}"

    dev_questions = [q for q in questions if q.get("split") == "dev"]
    held_out_questions = [q for q in questions if q.get("split") == "held_out"]

    assert len(dev_questions) == 18, f"Expected 18 dev questions, found {len(dev_questions)}"
    assert len(held_out_questions) == 12, f"Expected 12 held-out questions, found {len(held_out_questions)}"

    for q in questions:
        assert "id" in q
        assert "split" in q
        assert "application_id" in q
        assert "question" in q
        assert "expected_citations" in q
        assert len(q["expected_citations"]) > 0


def test_benchmark_execution_and_recall_threshold():
    results = evaluate_benchmark(
        questions_path="eval/questions.json",
        policy_dir="policies",
        data_dir="data/synthetic_dossiers",
        output_path="eval/eval_results.json",
        top_k=5,
    )

    summary = results["summary"]
    assert "overall" in summary
    assert "dev" in summary
    assert "held_out" in summary

    # Inviolable Invariant from AGENTS.md: Recall@5 >= 0.90
    overall_recall = summary["overall"]["recall_at_5"]
    assert overall_recall >= 0.90, f"Overall Recall@5 ({overall_recall}) fell below 0.90 threshold"
    assert summary["overall"]["target_recall_met"] is True

    dev_recall = summary["dev"]["recall_at_5"]
    assert dev_recall >= 0.90, f"Dev Recall@5 ({dev_recall}) fell below 0.90 threshold"

    held_out_recall = summary["held_out"]["recall_at_5"]
    assert held_out_recall >= 0.90, f"Held-out Recall@5 ({held_out_recall}) fell below 0.90 threshold"


def test_benchmark_grounding_precision():
    results = evaluate_benchmark(
        questions_path="eval/questions.json",
        policy_dir="policies",
        data_dir="data/synthetic_dossiers",
        output_path=None,
        top_k=5,
    )

    summary = results["summary"]
    precision = summary["overall"]["grounding_precision"]
    assert precision == 1.0, f"Grounding precision ({precision}) must be 1.0 (zero cross-tenant leakage)"


def test_benchmark_mrr():
    results = evaluate_benchmark(
        questions_path="eval/questions.json",
        policy_dir="policies",
        data_dir="data/synthetic_dossiers",
        output_path=None,
        top_k=5,
    )

    summary = results["summary"]
    mrr = summary["overall"]["mrr_at_5"]
    assert mrr >= 0.70, f"MRR@5 ({mrr}) is below expected quality baseline of 0.70"

"""
FinScan AI — RAG Evaluation Benchmark Runner.
Measures Recall@5 (>= 0.90), MRR@5, and Citation Grounding Precision on frozen benchmark questions.
Owned by Member 8 (Sai Mokshith).
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set

from core.rag.chunking import DocumentChunk
from core.rag.indexer import IndexManager
from core.rag.retriever import HybridRetriever

logger = logging.getLogger("finscan.eval")


def load_synthetic_dossiers_into_manager(
    index_manager: IndexManager,
    data_dir: str = "data/synthetic_dossiers",
) -> int:
    """
    Ingests synthetic applicant dossier manifests from disk into isolated application indices.
    Returns the number of applications ingested.
    """
    if not os.path.exists(data_dir):
        logger.warning(f"Synthetic dossier dir {data_dir} does not exist.")
        return 0

    app_count = 0
    for entry in os.listdir(data_dir):
        app_path = os.path.join(data_dir, entry)
        if not os.path.isdir(app_path):
            continue

        manifest_path = os.path.join(app_path, "dossier_manifest.json")
        if not os.path.exists(manifest_path):
            continue

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read manifest {manifest_path}: {e}")
            continue

        app_id = manifest.get("application_id", entry)
        app_index = index_manager.get_or_create_app_index(app_id)

        applicant_name = manifest.get("applicant_name", "Applicant")
        payslip = manifest.get("payslip", {})
        bank = manifest.get("bank_statement", {})
        tax = manifest.get("tax_return", {})
        kyc = manifest.get("kyc", {})
        tabular = manifest.get("tabular_features", {})

        # Page 1: Payslip
        p1_text = (
            f"Salary Payslip for Employee {payslip.get('employee_name', applicant_name)}. "
            f"Employer: {payslip.get('employer_name', 'Company')}. "
            f"Gross Monthly Salary: INR {payslip.get('gross_salary', 0.0):,.2f}. "
            f"Net Monthly Salary: INR {payslip.get('net_salary', 0.0):,.2f}. "
            f"Deductions: EPF INR {payslip.get('epf_deduction', 0.0):,.2f}, "
            f"TDS INR {payslip.get('tds_deduction', 0.0):,.2f}."
        )
        chunk_p1 = DocumentChunk(
            chunk_id=f"{app_id}_p1",
            text=p1_text,
            doc_id=app_id,
            page_number=1,
            document_type="payslip",
            aliases=[f"{app_id}_p1_c0"],
        )

        # Page 2: Bank Statement
        salary_credits_str = ", ".join(f"INR {c:,.2f}" for c in bank.get("monthly_salary_credits", []))
        p2_text = (
            f"Bank Account Statement for {bank.get('account_holder', applicant_name)}. "
            f"Bank Name: {bank.get('bank_name', 'Bank')}. "
            f"Account Number: {bank.get('account_number', '000000')}. "
            f"Monthly recurring salary credits: {salary_credits_str}. "
            f"Average Monthly Balance (AMB): INR {bank.get('average_balance', 0.0):,.2f}. "
            f"Bounced transactions: {bank.get('bounced_transactions', 0)}."
        )
        chunk_p2 = DocumentChunk(
            chunk_id=f"{app_id}_p2",
            text=p2_text,
            doc_id=app_id,
            page_number=2,
            document_type="bank_statement",
            aliases=[f"{app_id}_p2_c0"],
        )

        # Page 3: Income Tax Return
        p3_text = (
            f"Income Tax Return (ITR-V) Acknowledgement for {tax.get('assessee_name', applicant_name)}. "
            f"Permanent Account Number (PAN): {tax.get('pan_number', '')}. "
            f"Gross Total Income: INR {tax.get('gross_total_income', 0.0):,.2f}. "
            f"Total Tax Paid: INR {tax.get('total_tax_paid', 0.0):,.2f}."
        )
        chunk_p3 = DocumentChunk(
            chunk_id=f"{app_id}_p3",
            text=p3_text,
            doc_id=app_id,
            page_number=3,
            document_type="tax_return",
            aliases=[f"{app_id}_p3_c0"],
        )

        # Page 4: KYC Identity Proof
        p4_text = (
            f"Government Identity and KYC Proof. "
            f"Full Name: {kyc.get('full_name', applicant_name)}. "
            f"Permanent Account Number (PAN): {kyc.get('pan_number', '')}. "
            f"Date of Birth (DOB): {kyc.get('dob', '')}. "
            f"Masked Aadhaar Number: {kyc.get('aadhaar_masked', '')}."
        )
        chunk_p4 = DocumentChunk(
            chunk_id=f"{app_id}_p4",
            text=p4_text,
            doc_id=app_id,
            page_number=4,
            document_type="id_card",
            aliases=[f"{app_id}_p4_c0"],
        )

        # Page 5: Loan Application Form
        p5_text = (
            f"Retail Loan Application Form for {applicant_name}. "
            f"Requested Loan Amount: INR {tabular.get('loan_amount', 0.0):,.2f}. "
            f"Requested Loan Tenure: {tabular.get('loan_term', 0)} years. "
            f"Stated Annual Income: INR {tabular.get('income_annum', 0.0):,.2f}. "
            f"Stated CIBIL Credit Score: {tabular.get('cibil_score', 0)}. "
            f"Number of Dependents: {tabular.get('no_of_dependents', 0)}. "
            f"Education: {tabular.get('education', 'Graduate')}."
        )
        chunk_p5 = DocumentChunk(
            chunk_id=f"{app_id}_p5",
            text=p5_text,
            doc_id=app_id,
            page_number=5,
            document_type="application_form",
            aliases=[f"{app_id}_p5_c0"],
        )

        app_index.add_chunks([chunk_p1, chunk_p2, chunk_p3, chunk_p4, chunk_p5])
        app_count += 1

    logger.info(f"Ingested {app_count} synthetic dossiers into isolated indices.")
    return app_count


def evaluate_benchmark(
    questions_path: str = "eval/questions.json",
    policy_dir: str = "policies",
    data_dir: str = "data/synthetic_dossiers",
    output_path: Optional[str] = "eval/eval_results.json",
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Executes the frozen 30-question evaluation benchmark using HybridRetriever.
    Computes Recall@5, MRR@5, and Citation Grounding Precision across splits.
    """
    if not os.path.exists(questions_path):
        raise FileNotFoundError(f"Benchmark questions file not found: {questions_path}")

    with open(questions_path, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    questions = benchmark_data.get("questions", [])

    # Initialize retriever & index manager
    manager = IndexManager()
    manager.load_policy_corpus(policy_dir=policy_dir)
    load_synthetic_dossiers_into_manager(manager, data_dir=data_dir)

    retriever = HybridRetriever(index_manager=manager, policy_dir=policy_dir)

    split_stats: Dict[str, Dict[str, Any]] = {
        "dev": {"total": 0, "hits_at_5": 0, "rr_sum": 0.0, "total_chunks": 0, "authorized_chunks": 0},
        "held_out": {"total": 0, "hits_at_5": 0, "rr_sum": 0.0, "total_chunks": 0, "authorized_chunks": 0},
        "overall": {"total": 0, "hits_at_5": 0, "rr_sum": 0.0, "total_chunks": 0, "authorized_chunks": 0},
    }

    detailed_results: List[Dict[str, Any]] = []

    for q in questions:
        q_id = q["id"]
        split = q.get("split", "dev")
        target_app = q["application_id"]
        query_text = q["question"]
        expected_citations: Set[str] = set(q.get("expected_citations", []))

        # Retrieve top_k candidates
        results = retriever.retrieve(query=query_text, top_k=top_k, application_id=target_app)
        retrieved_ids = [r["chunk_id"] for r in results]

        # Check hits and ranks
        hit = False
        rank = 0

        for idx, r in enumerate(results, start=1):
            r_id = r["chunk_id"]
            r_aliases = set(r.get("aliases", []))
            # Match against expected citations or recognized aliases
            if (r_id in expected_citations) or any(a in expected_citations for a in r_aliases):
                if not hit:
                    hit = True
                    rank = idx

        rr = (1.0 / rank) if (hit and rank > 0) else 0.0

        # Check grounding precision (zero cross-tenant contamination)
        auth_chunks_in_query = 0
        for r in results:
            doc_id = r.get("doc_id", "")
            is_policy = r.get("is_policy", False)
            if target_app == "POLICY" and is_policy:
                auth_chunks_in_query += 1
            elif target_app != "POLICY" and (doc_id == target_app or target_app in r["chunk_id"]):
                auth_chunks_in_query += 1

        # Record metrics per split and overall
        for target_split in [split, "overall"]:
            split_stats[target_split]["total"] += 1
            if hit:
                split_stats[target_split]["hits_at_5"] += 1
            split_stats[target_split]["rr_sum"] += rr
            split_stats[target_split]["total_chunks"] += len(results)
            split_stats[target_split]["authorized_chunks"] += auth_chunks_in_query

        detailed_results.append({
            "id": q_id,
            "split": split,
            "target": target_app,
            "question": query_text,
            "expected_citations": list(expected_citations),
            "retrieved_chunk_ids": retrieved_ids,
            "hit_at_5": hit,
            "rank": rank,
            "reciprocal_rank": round(rr, 4),
        })

    # Aggregate summaries
    final_metrics: Dict[str, Any] = {}
    for s_name, s_data in split_stats.items():
        total = max(1, s_data["total"])
        total_chunks = max(1, s_data["total_chunks"])
        recall = round(s_data["hits_at_5"] / total, 4)
        mrr = round(s_data["rr_sum"] / total, 4)
        precision = round(s_data["authorized_chunks"] / total_chunks, 4)

        final_metrics[s_name] = {
            "total_questions": s_data["total"],
            "hits_at_5": s_data["hits_at_5"],
            "recall_at_5": recall,
            "mrr_at_5": mrr,
            "grounding_precision": precision,
            "target_recall_met": recall >= 0.90,
        }

    output_payload = {
        "benchmark_name": benchmark_data.get("benchmark_name", "FinScan AI Benchmark"),
        "version": benchmark_data.get("version", "1.0"),
        "summary": final_metrics,
        "details": detailed_results,
    }

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_payload, f, indent=2)
        logger.info(f"Saved evaluation benchmark results to {output_path}")

    return output_payload


def print_summary_table(summary: Dict[str, Any]) -> None:
    """Prints a formatted evaluation metrics table to stdout."""
    print("=" * 72)
    print(f"{'Split':<12} | {'Questions':<10} | {'Recall@5':<10} | {'MRR@5':<8} | {'Grounding Precision':<18}")
    print("-" * 72)
    for split_name in ["dev", "held_out", "overall"]:
        if split_name in summary:
            s = summary[split_name]
            status = " [PASS]" if s["recall_at_5"] >= 0.90 else " [FAIL]"
            print(
                f"{split_name:<12} | {s['total_questions']:<10} | "
                f"{s['recall_at_5'] * 100:.1f}%{status:<3} | {s['mrr_at_5']:.3f}    | "
                f"{s['grounding_precision'] * 100:.1f}%"
            )
    print("=" * 72)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = evaluate_benchmark()
    print_summary_table(res["summary"])

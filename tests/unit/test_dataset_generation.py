"""
Unit tests for Phase 4: Full Synthetic Dataset Generation.
Owned by Member 4 (Sravanthi).

Validates:
- Exactly 50 dossiers generated across the dataset
- Correct split counts: 25 dev, 10 tuning, 10 held-out, 5 demo
- Unique, stable dossier IDs with zero overlap across splits
- Deterministic regeneration producing identical files and metadata
- Required documents exist for every dossier based on scenario
- Comprehensive ground truth exists in every manifest
- Scenario metadata exists and all 8 discrepancy scenarios are represented
- No real customer PII is introduced and watermark is on all pages
"""

import json
import os
import pytest
import pymupdf

from scripts.generate_dossiers import (
    DATASET_SPLITS,
    SPLIT_SCENARIOS,
    SUPPORTED_SCENARIOS,
    WATERMARK_TEXT,
    generate_dataset,
    generate_dossier,
)


def test_dataset_split_configuration():
    assert DATASET_SPLITS["dev"] == 25
    assert DATASET_SPLITS["tuning"] == 10
    assert DATASET_SPLITS["held-out"] == 10
    assert DATASET_SPLITS["demo"] == 5
    assert sum(DATASET_SPLITS.values()) == 50

    for split_name, expected_count in DATASET_SPLITS.items():
        assert len(SPLIT_SCENARIOS[split_name]) == expected_count, (
            f"Scenario count mismatch for {split_name}"
        )


def test_all_supported_scenarios_represented_in_dataset():
    all_assigned_scenarios = set()
    for scenarios in SPLIT_SCENARIOS.values():
        all_assigned_scenarios.update(scenarios)

    for scenario in SUPPORTED_SCENARIOS:
        assert scenario in all_assigned_scenarios, (
            f"Scenario '{scenario}' not represented in dataset"
        )


def test_generate_dataset_structure_and_counts(tmp_path):
    output_dir = str(tmp_path / "synthetic_dossiers")
    manifest = generate_dataset(output_dir=output_dir, base_seed=1)

    assert manifest["total_dossiers"] == 50
    assert manifest["split_counts"]["dev"] == 25
    assert manifest["split_counts"]["tuning"] == 10
    assert manifest["split_counts"]["held-out"] == 10
    assert manifest["split_counts"]["demo"] == 5

    # Check master split manifest file on disk
    splits_file = os.path.join(output_dir, "dataset_splits.json")
    assert os.path.exists(splits_file)
    with open(splits_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["total_dossiers"] == 50
    assert loaded["split_counts"] == manifest["split_counts"]


def test_dataset_unique_stable_ids_and_no_split_overlap(tmp_path):
    output_dir = str(tmp_path / "synthetic_dossiers")
    manifest = generate_dataset(output_dir=output_dir, base_seed=1)

    all_ids = []
    seen_ids = set()

    for split_name, app_ids in manifest["splits"].items():
        for app_id in app_ids:
            assert app_id not in seen_ids, f"Duplicate ID found: {app_id} in split {split_name}"
            seen_ids.add(app_id)
            all_ids.append(app_id)

    assert len(all_ids) == 50
    assert len(seen_ids) == 50

    # Ensure stable formatting e.g. APP-00001 to APP-00050
    for idx, app_id in enumerate(all_ids, 1):
        assert app_id == f"APP-{idx:05d}"


def test_deterministic_regeneration(tmp_path):
    run1_dir = str(tmp_path / "run1")
    run2_dir = str(tmp_path / "run2")

    m1 = generate_dataset(output_dir=run1_dir, base_seed=10)
    m2 = generate_dataset(output_dir=run2_dir, base_seed=10)

    assert m1["total_dossiers"] == m2["total_dossiers"]
    assert m1["splits"] == m2["splits"]

    # Pick a dossier and check manifest bit-for-bit equality
    sample_id = "APP-00015"
    p1 = os.path.join(run1_dir, sample_id, "dossier_manifest.json")
    p2 = os.path.join(run2_dir, sample_id, "dossier_manifest.json")

    with open(p1, "r", encoding="utf-8") as f1, open(p2, "r", encoding="utf-8") as f2:
        assert json.load(f1) == json.load(f2)


def test_required_documents_exist_per_scenario(tmp_path):
    output_dir = str(tmp_path / "synthetic_dossiers")
    manifest = generate_dataset(output_dir=output_dir, base_seed=1)

    for app_id, summary in manifest["dossiers"].items():
        app_dir = os.path.join(output_dir, app_id)
        scenario = summary["scenario"]

        assert os.path.exists(os.path.join(app_dir, "application.pdf"))
        assert os.path.exists(os.path.join(app_dir, "bank_statement.pdf"))
        assert os.path.exists(os.path.join(app_dir, "kyc.pdf"))
        assert os.path.exists(os.path.join(app_dir, "dossier_manifest.json"))

        if scenario == "missing_payslip":
            assert not os.path.exists(os.path.join(app_dir, "payslip_1.pdf"))
        else:
            assert os.path.exists(os.path.join(app_dir, "payslip_1.pdf"))
            assert os.path.exists(os.path.join(app_dir, "payslip_2.pdf"))
            assert os.path.exists(os.path.join(app_dir, "payslip_3.pdf"))

        if scenario == "missing_itr":
            assert not os.path.exists(os.path.join(app_dir, "itr.pdf"))
        else:
            assert os.path.exists(os.path.join(app_dir, "itr.pdf"))


def test_ground_truth_and_scenario_metadata_completeness(tmp_path):
    output_dir = str(tmp_path / "synthetic_dossiers")
    manifest = generate_dataset(output_dir=output_dir, base_seed=1)

    for app_id, summary in manifest["dossiers"].items():
        manifest_path = os.path.join(output_dir, app_id, "dossier_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            dossier_manifest = json.load(f)

        # Validate scenario and split metadata
        assert dossier_manifest["scenario"] == summary["scenario"]
        assert dossier_manifest["split"] == summary["split"]
        assert dossier_manifest["seed"] == summary["seed"]

        # Validate applicant facts
        applicant_facts = dossier_manifest["applicant_facts"]
        assert "full_name" in applicant_facts
        assert "pan_number" in applicant_facts
        assert "aadhaar_masked" in applicant_facts
        assert "employer_name" in applicant_facts

        # Validate financial ground truth
        fin = dossier_manifest["financial_ground_truth"]
        assert fin["gross_monthly_salary"] > 0
        assert fin["net_monthly_salary"] > 0
        assert fin["bank_monthly_salary_credit"] > 0
        assert fin["annualized_gross_income"] > 0
        assert fin["itr_gross_total_income"] > 0

        # Validate expected rule outcomes
        rules = dossier_manifest["expected_rule_outcomes"]
        assert "RULE-COMP-01" in rules
        assert "RULE-INC-01" in rules
        assert "RULE-TAX-01" in rules
        assert "RULE-ID-01" in rules
        for verdict in rules.values():
            assert verdict in ("pass", "flag", "unknown")


def test_no_real_pii_and_mandatory_watermark(tmp_path):
    output_dir = str(tmp_path / "synthetic_dossiers")
    manifest = generate_dataset(output_dir=output_dir, base_seed=1)

    # Inspect all dossiers in demo split and a sample from each other split
    sample_ids = manifest["splits"]["demo"] + [
        manifest["splits"]["dev"][0],
        manifest["splits"]["tuning"][0],
        manifest["splits"]["held-out"][0],
    ]

    for app_id in sample_ids:
        app_dir = os.path.join(output_dir, app_id)
        manifest_path = os.path.join(app_dir, "dossier_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            m = json.load(f)

        # Synthetic PAN invariant (starts with ABCDE, ends with F)
        pan = m["applicant_facts"]["pan_number"]
        assert pan.startswith("ABCDE") and pan.endswith("F")

        # Masked Aadhaar invariant
        aadhaar = m["applicant_facts"]["aadhaar_masked"]
        assert aadhaar.startswith("XXXX-XXXX-")

        # Verify bold watermark on all rendered PDF pages
        for doc_name in m["generated_document_names"]:
            if doc_name.endswith(".pdf"):
                doc_path = os.path.join(app_dir, doc_name)
                doc = pymupdf.open(doc_path)
                assert len(doc) >= 1
                for page in doc:
                    page_text = page.get_text()
                    assert WATERMARK_TEXT in page_text, (
                        f"Mandatory watermark missing from {doc_name} in {app_id}"
                    )
                doc.close()

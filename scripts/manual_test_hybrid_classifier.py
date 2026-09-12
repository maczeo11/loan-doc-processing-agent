"""
Standalone manual test for the hybrid cascade classifier
(ml/classifier/hybrid_cascade.py) - shows baseline vs. hybrid side by side on
a few sample pages, including one deliberately ambiguous one meant to land in
the escalation band.

Usage:
    python scripts/manual_test_hybrid_classifier.py

Needs a trained DistilBERT artifact at ml/artifacts/distilbert/ to actually
escalate (run `python -m ml.classifier.train_challenger` first) - without it,
escalation falls through to DistilBertClassifier's keyword-heuristic fallback,
which still runs but isn't a real second opinion.
"""

from ml.classifier.baseline_tfidf import predict_with_details
from ml.classifier.hybrid_cascade import HybridCascadeClassifier

SAMPLES = {
    "clear_payslip": "PAYSLIP FOR THE MONTH OF MARCH 2024. Employee: Jane Doe. Basic Salary: 50,000. Net Pay: 45,000.",
    "clear_tax_return": (
        "FORM NO. 16 [See rule 31(1)(a)] Certificate under section 203 of the Income-tax Act, 1961. "
        "Assessment Year: 2024-25. Total Tax Deducted and Deposited to Central Government."
    ),
    "ambiguous_short": "statement account details enclosed for reference month",
    "gibberish": "asdkj alksjd laksjd 12345 %%% random text not a document at all",
}

cascade = HybridCascadeClassifier()

print(f"{'Sample':<20} {'Baseline':<22} {'Hybrid':<22} {'Escalated?'}")
print("-" * 80)
for name, text in SAMPLES.items():
    base = predict_with_details(text)
    hybrid = cascade.predict_with_details(text)
    base_label = f"{base['predicted_type']} ({base['confidence']:.2f})"
    hybrid_label = f"{hybrid['predicted_type']} ({hybrid['confidence']:.2f})"
    print(f"{name:<20} {base_label:<22} {hybrid_label:<22} {hybrid['escalated_to_distilbert']}")

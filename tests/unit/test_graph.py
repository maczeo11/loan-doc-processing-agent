"""
Unit tests for LangGraph StateGraph nodes, workflow, and human-in-the-loop interrupt.
"""

from langgraph.checkpoint.memory import MemorySaver
from core.contracts.state import LoanApplicationState
from core.contracts.evidence import EvidenceRef, BoundingBox
from core.contracts.facts import PayslipFacts, BankStatementFacts, TaxReturnFacts, ApplicantFact, MoneyFact
from core.graph.workflow import build_application_graph


def create_initial_state(app_id: str = "APP-TEST-001") -> LoanApplicationState:
    bbox = BoundingBox(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    ev = EvidenceRef(
        document_id=f"{app_id}-doc1",
        document_type="payslip",
        page_number=1,
        quoted_span="Net Pay: INR 50,000",
        bounding_box=bbox,
    )

    payslip = PayslipFacts(
        employee_name="John Doe",
        employer_name="Acme Corp",
        gross_salary=MoneyFact(amount=60000, currency="INR", source=ev),
        net_salary=MoneyFact(amount=50000, currency="INR", source=ev),
    )

    bank = BankStatementFacts(
        account_holder="John Doe",
        bank_name="HDFC Bank",
        account_number_masked="XXXXXX1234",
        salary_credits=[MoneyFact(amount=50000, currency="INR", source=ev)],
        average_salary_credit=MoneyFact(amount=50000, currency="INR", source=ev),
        closing_balance=MoneyFact(amount=40000, currency="INR", source=ev),
        bounced_transactions=0,
    )

    tax = TaxReturnFacts(
        assessee_name="John Doe",
        pan_number="ABCDE1234F",
        assessment_year="2025-26",
        gross_total_income=MoneyFact(amount=720000, currency="INR", source=ev),
        total_tax_paid=MoneyFact(amount=20000, currency="INR", source=ev),
    )

    applicant = ApplicantFact(
        full_name="John Doe",
        source_name=ev,
        pan_number="ABCDE1234F",
        source_pan=ev,
    )

    return {
        "application_id": app_id,
        "status": "QUEUED",
        "status_history": [],
        "document_ids": [f"{app_id}-doc1", f"{app_id}-doc2", f"{app_id}-doc3", f"{app_id}-doc4", f"{app_id}-doc5"],
        "document_manifest": {
            f"{app_id}-doc1": "s3://bucket/payslip.pdf",
            f"{app_id}-doc2": "s3://bucket/bank.pdf",
            f"{app_id}-doc3": "s3://bucket/tax.pdf",
            f"{app_id}-doc4": "s3://bucket/pan_id.pdf",
            f"{app_id}-doc5": "s3://bucket/application_form.pdf",
        },
        "classified_types": {
            f"{app_id}-doc1": "payslip",
            f"{app_id}-doc2": "bank_statement",
            f"{app_id}-doc3": "tax_acknowledgement",
            f"{app_id}-doc4": "id_card",
            f"{app_id}-doc5": "application_form",
        },
        "applicant": applicant,
        "payslip": payslip,
        "bank_statement": bank,
        "tax_return": tax,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": False,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }


def test_graph_compilation():
    graph = build_application_graph()
    assert graph is not None


def test_graph_execution_happy_path():
    graph = build_application_graph(enable_interrupt=False)
    state = create_initial_state()

    result = graph.invoke(state)

    assert result["status"] == "READY_FOR_REVIEW"
    assert result["review_paused"] is True
    assert len(result["findings"]) == 5

    # Verify all 5 deterministic rules fired
    rule_ids = [f.rule_id for f in result["findings"]]
    assert "RULE-COMP-01" in rule_ids
    assert "RULE-INC-01" in rule_ids
    assert "RULE-TAX-01" in rule_ids
    assert "RULE-ID-01" in rule_ids
    assert "RULE-BANK-01" in rule_ids

    # Verify summary and grounding
    assert result["summary_markdown"] is not None
    assert "Credit Appraisal Memo" in result["summary_markdown"]
    assert result["summary_grounded"] is True


def test_graph_execution_empty_dossier_fails():
    graph = build_application_graph(enable_interrupt=False)
    state: LoanApplicationState = {
        "application_id": "APP-EMPTY",
        "status": "QUEUED",
        "status_history": [],
        "document_ids": [],
        "document_manifest": {},
        "classified_types": {},
        "applicant": None,
        "payslip": None,
        "bank_statement": None,
        "tax_return": None,
        "findings": [],
        "missing_documents": [],
        "retrieved_chunk_ids": [],
        "summary_markdown": None,
        "summary_grounded": False,
        "review_paused": False,
        "reviewer_decision": None,
        "reviewer_notes": None,
        "corrections_applied": [],
    }

    result = graph.invoke(state)
    assert result["status"] == "FAILED"
    assert len(result["missing_documents"]) == 5


def test_graph_with_checkpointer_and_interrupt():
    memory = MemorySaver()
    graph = build_application_graph(checkpointer=memory, enable_interrupt=True)
    state = create_initial_state("APP-INTERRUPT-001")
    config = {"configurable": {"thread_id": "thread-app-001"}}

    # Phase 1: Run until interrupt before human_review
    interrupted_result = graph.invoke(state, config=config)
    assert interrupted_result["status"] == "READY_FOR_REVIEW"
    assert interrupted_result["review_paused"] is True
    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_review",)

    # Phase 2: Underwriter submits sign-off decision (Approved)
    graph.update_state(
        config,
        {
            "reviewer_decision": "APPROVED",
            "reviewer_notes": "All verified against bank statement credits.",
        }
    )

    # Phase 3: Resume graph from interrupt checkpoint to completion
    resumed_result = graph.invoke(None, config=config)
    assert resumed_result["status"] == "REVIEWED"
    assert resumed_result["review_paused"] is False

    # Check status history records final review transition
    history = resumed_result["status_history"]
    last_transition = history[-1]
    assert last_transition["to_status"] == "REVIEWED"
    assert "Underwriter sign-off submitted: APPROVED" in last_transition["reason"]


def test_sqlite_saver_persists_across_instances(tmp_path):
    from core.graph.checkpoint import SqliteSaver
    from core.graph.workflow import resume_application_review

    db_file = str(tmp_path / "checkpoints.sqlite3")
    saver1 = SqliteSaver(db_path=db_file)
    graph1 = build_application_graph(checkpointer=saver1, enable_interrupt=True)
    state = create_initial_state("APP-SQLITE-001")
    config = {"configurable": {"thread_id": "thread-sqlite-001"}}

    # Process 1 executes up to interrupt
    result1 = graph1.invoke(state, config=config)
    assert result1["status"] == "READY_FOR_REVIEW"

    # Process 2 loads separate checkpointer from same db
    saver2 = SqliteSaver(db_path=db_file)
    graph2 = build_application_graph(checkpointer=saver2, enable_interrupt=True)
    snapshot = graph2.get_state(config)
    assert snapshot.next == ("human_review",)
    assert snapshot.values.get("status") == "READY_FOR_REVIEW"

    # Resume via helper function
    final_state = resume_application_review(
        thread_id="thread-sqlite-001",
        decision="APPROVED",
        notes="Audit passed on durable database",
        checkpointer=saver2,
    )
    assert final_state["status"] == "REVIEWED"
    assert final_state["review_paused"] is False


def test_resume_application_review_needs_info(tmp_path):
    from core.graph.checkpoint import SqliteSaver
    from core.graph.workflow import resume_application_review

    db_file = str(tmp_path / "checkpoints_needs_info.sqlite3")
    saver = SqliteSaver(db_path=db_file)
    graph = build_application_graph(checkpointer=saver, enable_interrupt=True)
    state = create_initial_state("APP-NEEDS-INFO-001")
    config = {"configurable": {"thread_id": "thread-needs-info-001"}}

    graph.invoke(state, config=config)

    final_state = resume_application_review(
        thread_id="thread-needs-info-001",
        decision="NEEDS_INFO",
        notes="Bank statement missing page 3.",
        checkpointer=saver,
    )
    assert final_state["status"] == "NEEDS_INFORMATION"
    assert final_state["review_paused"] is False

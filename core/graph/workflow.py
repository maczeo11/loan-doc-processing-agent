"""
StateGraph Assembly & Checkpointer Compilation.
Owned by Member 2 (Bhanu Teja).

Orchestrates the sequential loan document processing pipeline with:
- Deterministic branching (triage failure routing)
- Strict typed LoanApplicationState transitions
- Human-in-the-loop interrupt() checkpoint before human underwriter review
"""

from typing import Optional, Literal
from langgraph.graph import StateGraph, END
from core.contracts.state import LoanApplicationState
from core.graph.nodes import (
    triage_node,
    ocr_and_classify_node,
    extract_facts_node,
    evaluate_rules_node,
    retrieve_policy_node,
    synthesize_summary_node,
    validate_grounding_node,
    human_review_node,
)


def route_after_triage(state: LoanApplicationState) -> Literal["ocr_and_classify", "__end__"]:
    """
    Conditional routing edge after triage.
    If dossier validation failed (e.g. zero documents), terminate pipeline immediately.
    """
    if state.get("status") == "FAILED":
        return "__end__"
    return "ocr_and_classify"


def build_application_graph(checkpointer=None, enable_interrupt: bool = True):
    """
    Constructs and compiles the authoritative Loan Processing StateGraph.
    
    Args:
        checkpointer: Optional persistence checkpointer (e.g. PostgresSaver or MemorySaver).
        enable_interrupt: If True and checkpointer is provided, pauses before human_review.
    """
    workflow = StateGraph(LoanApplicationState)

    # 1. Add processing nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("ocr_and_classify", ocr_and_classify_node)
    workflow.add_node("extract_facts", extract_facts_node)
    workflow.add_node("evaluate_rules", evaluate_rules_node)
    workflow.add_node("retrieve_policy", retrieve_policy_node)
    workflow.add_node("synthesize_summary", synthesize_summary_node)
    workflow.add_node("validate_grounding", validate_grounding_node)
    workflow.add_node("human_review", human_review_node)

    # 2. Define entry point and conditional branching
    workflow.set_entry_point("triage")
    workflow.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "ocr_and_classify": "ocr_and_classify",
            "__end__": END,
        }
    )

    # 3. Define sequential pipeline edges
    workflow.add_edge("ocr_and_classify", "extract_facts")
    workflow.add_edge("extract_facts", "evaluate_rules")
    workflow.add_edge("evaluate_rules", "retrieve_policy")
    workflow.add_edge("retrieve_policy", "synthesize_summary")
    workflow.add_edge("synthesize_summary", "validate_grounding")
    workflow.add_edge("validate_grounding", "human_review")
    workflow.add_edge("human_review", END)

    # 4. Compile with durable interrupt checkpoint before human review
    interrupt_nodes = ["human_review"] if (checkpointer is not None and enable_interrupt) else []

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_nodes,
    )


# Backward compatibility alias
build_loan_processing_graph = build_application_graph

"""
StateGraph Assembly & PostgreSQL Checkpointer Compilation.
Owned by Member 2 (Bhanu Teja).
"""

from langgraph.graph import StateGraph, END
from core.contracts.state import LoanApplicationState
from core.graph.nodes import (
    triage_and_validate_node,
    extract_fields_node,
    evaluate_rules_node,
    retrieve_policy_node,
    synthesize_summary_node,
)


def build_loan_processing_graph(checkpointer=None):
    """
    Constructs the compiled StateGraph with durable pause-and-resume for human review.
    """
    workflow = StateGraph(LoanApplicationState)

    # Add processing nodes
    workflow.add_node("triage", triage_and_validate_node)
    workflow.add_node("extract", extract_fields_node)
    workflow.add_node("rules", evaluate_rules_node)
    workflow.add_node("retrieve", retrieve_policy_node)
    workflow.add_node("synthesize", synthesize_summary_node)

    # Define linear execution edges
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "extract")
    workflow.add_edge("extract", "rules")
    workflow.add_edge("rules", "retrieve")
    workflow.add_edge("retrieve", "synthesize")
    workflow.add_edge("synthesize", END)

    # Compile with interrupt before human review
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[]  # Set to ["review"] when human review node is linked
    )

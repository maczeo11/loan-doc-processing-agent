"""
Read-only retrieval helpers for the agentic Q&A path (apps/api/agent.py).

These are plain functions with no LLM SDK import — they only wrap the existing
HybridRetriever (core/rag/retriever.py). The LangChain/LangGraph tool-calling
machinery lives in apps/api/agent.py, keeping core/ free of provider SDKs per
the ports/adapters rule (AGENTS.md §3).

Owned by Member 8 (Sai Mokshith) per core/rag/ module boundaries.
"""

from typing import Any, Dict, List

from core.rag.retriever import HybridRetriever


def search_policy_passages(retriever: HybridRetriever, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search the underwriting policy corpus. Read-only, no side effects."""
    return retriever.retrieve_policy(query, top_k=top_k)


def search_dossier_passages(
    retriever: HybridRetriever, application_id: str, query: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Search one applicant's own uploaded dossier documents. Read-only, no side effects."""
    return retriever.retrieve_dossier(application_id, query, top_k=top_k)


def format_hits_for_llm(hits: List[Dict[str, Any]]) -> str:
    """
    Renders retrieval hits as numbered, citation-tagged passages for a tool-call
    result the LLM reads back. Mirrors the citation format the grounding firewall
    (core/rag/grounding.py) expects: `[chunk_id]` bracket tags in the narrative.
    """
    if not hits:
        return "No matching passages found."
    lines = []
    for i, hit in enumerate(hits, start=1):
        chunk_id = hit.get("chunk_id", "UNKNOWN")
        text = str(hit.get("text", "")).strip()
        excerpt = text[:500] + ("..." if len(text) > 500 else "")
        lines.append(f"{i}. [{chunk_id}] {excerpt}")
    return "\n".join(lines)

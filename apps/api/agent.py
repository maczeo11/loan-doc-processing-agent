"""
Optional tool-calling agent for the underwriter Q&A endpoint
(POST /applications/{id}/questions in apps/api/routes/review.py).

Scope, by design:
- Read-only tools only (policy search). No tool may compute a verdict, write
  data, or call into core/rules/.
- The agent's final answer is re-validated by core/rag/grounding.py before it
  reaches the underwriter — the same firewall the CAM narrative already goes
  through — so tool-calling autonomy never bypasses the Prime Invariant.
- Fully additive and feature-flagged (settings.AGENTIC_QA_ENABLED, default
  False). Disabled or on any failure, callers fall back to the existing
  single-shot llm.answer_question() path untouched.

NOTE: core/rag/retriever.py::retrieve_dossier and IndexManager.get_or_create_app_index
exist and are exercised in eval/run_eval.py and tests/unit/test_rag.py, but no
production pipeline populates a per-application index at request time - nothing
in core/graph/nodes.py ever calls get_or_create_app_index. A "search this
applicant's own documents" tool would therefore silently return nothing every
time, so it is deliberately NOT included here. Wiring dossier retrieval into
this agent is real future work, gated on first building that indexing
pipeline (e.g. in ocr_and_classify_node/extract_facts_node) - see
docs/improvement_roadmap.md.

Owned by Member 6 (Balaji) per apps/api/ module boundaries; the retrieval
helpers it calls live in core/rag/tools.py (Member 8's zone).
"""

import logging
import os
from typing import Any, Dict, List, Optional

from core.rag.grounding import DISPOSITION_PATTERNS, sanitize_summary_text
from core.rag.retriever import HybridRetriever
from core.rag.tools import format_hits_for_llm, search_policy_passages

logger = logging.getLogger("finscan.api.agent")

# Cap on ReAct loop steps so a misbehaving/adversarial prompt can't spin forever.
AGENT_RECURSION_LIMIT = 6


def get_agentic_chat_model() -> Optional[Any]:
    """
    Builds a LangChain ChatOpenAI client pointed at whichever backend
    OpenCodeZenLLM (adapters/llm/opencode.py) would resolve to (Groq or
    OpenCode Zen) - reusing its exact env-var resolution so this never drifts
    from the adapter's own defaults. Returns None if no key is configured.
    """
    if not (os.getenv("GROQ_API_KEY") or os.getenv("OPENCODE_API_KEY")):
        return None
    try:
        from langchain_openai import ChatOpenAI

        from adapters.llm.opencode import OpenCodeZenLLM

        resolved = OpenCodeZenLLM()  # resolves api_key/base_url/model from env, no network call
        return ChatOpenAI(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            model=resolved.model,
            temperature=0.0,
        )
    except Exception as exc:  # noqa: BLE001 - any import/config failure just disables the path
        logger.warning(f"Agentic chat model unavailable, falling back to single-shot LLM: {exc}")
        return None


def answer_question_agentic(
    question: str,
    retriever: HybridRetriever,
) -> Optional[Dict[str, Any]]:
    """
    Runs a read-only ReAct agent (policy search only - see module docstring
    for why dossier search isn't included yet) to answer an underwriter's
    question, then firewalls the result through core/rag/grounding.py before
    returning it.

    Returns {"answer": str, "citations": List[Dict], "chunk_ids": List[str]}
    on success, or None if the agentic path isn't available/fails - callers
    must fall back to the existing single-shot answer_question() path.
    """
    chat_model = get_agentic_chat_model()
    if chat_model is None:
        return None

    try:
        from langchain_core.tools import tool
        from langgraph.prebuilt import create_react_agent
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"langgraph/langchain-core unavailable for agentic Q&A: {exc}")
        return None

    session_hits: List[Dict[str, Any]] = []

    @tool
    def search_policy(query: str) -> str:
        """Search the underwriting policy corpus for guidance relevant to the query."""
        hits = search_policy_passages(retriever, query)
        session_hits.extend(hits)
        return format_hits_for_llm(hits)

    system_prompt = (
        "You are an underwriter's research assistant. Answer STRICTLY using the "
        "search_policy tool - never from memory or assumption. Cite every fact "
        "with its [chunk_id] bracket tag. Never state whether the loan should be "
        "approved, rejected, or sanctioned - that is a human decision. If the "
        "tool doesn't return an answer, say so plainly."
    )

    try:
        agent = create_react_agent(chat_model, [search_policy], prompt=system_prompt)
        result = agent.invoke(
            {"messages": [("user", question)]},
            config={"recursion_limit": AGENT_RECURSION_LIMIT},
        )
        final_message = result["messages"][-1]
        answer_text = getattr(final_message, "content", "") or ""
    except Exception as exc:  # noqa: BLE001 - agent errors fall back, never surface raw to the user
        logger.warning(f"Agentic Q&A run failed, falling back to single-shot LLM: {exc}")
        return None

    chunk_ids = [h.get("chunk_id") for h in session_hits if h.get("chunk_id")]
    grounded_answer = sanitize_summary_text(answer_text, authorized_chunk_ids=chunk_ids)

    # sanitize_summary_text only strips unauthorized citations. Unlike the CAM
    # narrative path (validate_llm_narrative), it doesn't check for autonomous
    # disposition language - and validate_llm_narrative can't be reused as-is
    # here because it hard-fails whenever findings=[] (always true for Q&A).
    # Defense in depth: redact any approve/reject/sanction language ourselves.
    for pattern in DISPOSITION_PATTERNS:
        if pattern.search(grounded_answer):
            grounded_answer = (
                "> ⚠️ [ABSTENTION: Response withheld - it contained autonomous "
                "disposition language, which this assistant is not authorized to "
                "provide. Only a human underwriter may approve, reject, or "
                "sanction an application.]"
            )
            break

    citations = [
        {
            "chunk_id": h.get("chunk_id"),
            "policy_id": h.get("doc_id") if h.get("is_policy") else None,
            "document_id": h.get("doc_id") if not h.get("is_policy") else None,
            "page_number": h.get("page_number"),
            "score": h.get("score"),
            "text": h.get("text"),
        }
        for h in session_hits
    ]

    return {"answer": grounded_answer, "citations": citations, "chunk_ids": chunk_ids}

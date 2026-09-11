"""
Standalone manual test for the agentic Q&A path (apps/api/agent.py) - no
Docker/Postgres needed, just a real GROQ_API_KEY (or OPENCODE_API_KEY).

Usage (PowerShell):
    $env:GROQ_API_KEY = "gsk_..."
    python scripts/manual_test_agentic_qa.py "What is the maximum debt-to-income ratio allowed?"
"""

import sys

from apps.api.agent import answer_question_agentic
from core.rag.indexer import IndexManager
from core.rag.retriever import HybridRetriever

question = sys.argv[1] if len(sys.argv) > 1 else "What is the maximum debt-to-income ratio allowed?"

print(f"Question: {question}\n")

manager = IndexManager()
manager.load_policy_corpus(policy_dir="policies")
retriever = HybridRetriever(index_manager=manager, policy_dir="policies")

result = answer_question_agentic(question, retriever)

if result is None:
    print("Agentic path unavailable (no API key configured, or it failed - check logs above).")
    print("Set GROQ_API_KEY or OPENCODE_API_KEY and try again.")
else:
    print("Answer:")
    print(result["answer"])
    print(f"\nCitations used ({len(result['citations'])}):")
    for c in result["citations"]:
        print(f"  [{c['chunk_id']}] {str(c['text'])[:100]}...")

"""
LLMPort: Text generation and structured summary protocol.
"""

from typing import Protocol, List, Dict, Any


class LLMPort(Protocol):
    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        """Generate cited loan review narrative."""
        ...

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        """Answer reviewer inquiry strictly from retrieved context."""
        ...

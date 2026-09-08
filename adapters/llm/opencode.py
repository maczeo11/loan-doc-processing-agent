"""
OpenCode Zen (OpenAI-compatible) adapter for development & cloud generation.
"""

from typing import List, Dict, Any
from adapters.llm.base import LLMPort


class OpenCodeZenLLM(LLMPort):
    def __init__(self, api_key: str, base_url: str = "https://opencode.ai/zen/v1", model: str = "zen-small"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        # TODO: Member 8 / Bhanu implement OpenAI-compatible chat completion
        return "Summary placeholder"

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        # TODO: Member 8 implement Q&A over retrieved passages
        return "Answer placeholder"

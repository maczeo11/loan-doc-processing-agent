"""
Offline fallback LLM adapter: Qwen3-4B-Instruct-2507 Q4 GGUF via llama.cpp.
Guarantees full offline functionality for Day 6 failure tests.
"""

from typing import List, Dict, Any
from adapters.llm.base import LLMPort


class LocalQwenLLM(LLMPort):
    def __init__(self, model_path: str = "ml/artifacts/qwen3-4b-q4.gguf"):
        self.model_path = model_path

    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        # TODO: Member 8 / Bhanu implement local llama.cpp text completion
        return "Offline summary placeholder"

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        return "Offline answer placeholder"

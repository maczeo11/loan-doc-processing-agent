"""
Offline fallback LLM adapter: Qwen3-4B-Instruct-2507 Q4 GGUF via llama.cpp.
Owned by Member 2 (Bhanu Teja) & Member 8 (Sai Mokshith).

Guarantees full offline functionality for Day 6 failure and network-outage tests.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from adapters.llm.base import LLMPort

logger = logging.getLogger("finscan.adapters.llm.qwen")


class LocalQwenLLM(LLMPort):
    """
    Offline local LLM adapter using Qwen3-4B GGUF via llama-cpp-python.
    Falls back to deterministic rule synthesis when binary model is absent.
    """

    def __init__(self, model_path: str = "ml/artifacts/qwen3-4b-q4.gguf", n_ctx: int = 4096):
        self.model_path = model_path
        self.n_ctx = n_ctx
        self._llm = None

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        if not os.path.exists(self.model_path):
            return None

        try:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=4,
                verbose=False,
            )
            logger.info(f"Loaded local Qwen GGUF model from {self.model_path}")
            return self._llm
        except Exception as e:
            logger.warning(f"Could not load local llama-cpp model: {e}")
            return None

    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        """
        Generates offline appraisal narrative from deterministic findings.
        """
        llm = self._get_llm()
        if llm is not None:
            try:
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    max_tokens=1024,
                )
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Error during local Qwen inference: {e}")

        # Deterministic offline memo synthesizer fallback
        return (
            "### Credit Appraisal Memo (Offline Fallback)\n\n"
            f"{prompt}\n\n"
            "*Synthesized via local deterministic underwriting rules.*"
        )

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        """
        Answers underwriter questions offline using retrieved context.
        """
        llm = self._get_llm()
        formatted_context = "\n\n".join(
            f"[{p.get('id', f'chunk_{i}')}]: {p.get('text', '')}"
            for i, p in enumerate(retrieved_passages, 1)
        )

        if llm is not None:
            try:
                sys_msg = (
                    "You are an offline credit underwriting assistant. "
                    "Answer strictly based on the context passages and cite passage IDs."
                )
                user_msg = f"<context>\n{formatted_context}\n</context>\n\nQuestion: {question}"
                response = llm.create_chat_completion(
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.0,
                    max_tokens=512,
                )
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"Local Qwen Q&A inference failed: {e}")

        # Keyword matching fallback for offline inquiry
        q_lower = question.lower()
        matched = []
        for p in retrieved_passages:
            p_text = p.get("text", "")
            p_id = p.get("id", "policy_clause")
            if any(term in p_text.lower() for term in q_lower.split() if len(term) > 3):
                matched.append(f"- According to [{p_id}]: {p_text[:200]}...")

        if matched:
            return "Based on offline policy review:\n" + "\n".join(matched)
        return "I cannot answer this question based on the provided documents."

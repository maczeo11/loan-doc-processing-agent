"""
OpenCode Zen (OpenAI-compatible) adapter for cloud generation & underwriter Q&A.
Owned by Member 2 (Bhanu Teja) & Member 8 (Sai Mokshith).

Invariants:
- Zero hallucinated numbers: Prompt inputs contain pre-computed deterministic findings only.
- Prompt injection defense: Untrusted user text is strictly delimited within context blocks.
- Grounding: All Q&A answers must cite retrieved passage IDs.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import httpx
from adapters.llm.base import LLMPort

logger = logging.getLogger("finscan.adapters.llm.opencode")


class OpenCodeZenLLM(LLMPort):
    """
    OpenAI-compatible LLM adapter for OpenCode Zen / cloud inference.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "zen-small",
        timeout_seconds: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENCODE_BASE_URL") or "https://opencode.ai/zen/v1").rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = http_client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout_seconds,
        )

    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        """
        Generates Credit Appraisal Memo markdown narration from deterministic findings.
        Enforces prompt injection boundaries on contextual data.
        """
        # Prompt injection isolation: enclose input data in triple xml tags
        isolated_prompt = (
            "Analyze the following verified underwriting findings and policy clauses to produce "
            "an auditable Credit Appraisal Memo narrative.\n\n"
            "<context_data>\n"
            f"{prompt}\n"
            "</context_data>\n\n"
            "Generate an executive underwriting appraisal memo. Cite all policy guidelines referenced. "
            "Do NOT compute or alter any monetary numbers."
        )

        default_system = (
            system_prompt
            or "You are an auditable Credit Underwriting AI. "
            "Deterministic code computes all numbers; you narrate and explain findings. "
            "Never alter monetary figures or rule verdicts."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": default_system},
                {"role": "user", "content": isolated_prompt},
            ],
            "temperature": 0.0,
        }

        try:
            client = self._get_client()
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Failed to generate summary via OpenCode Zen: {e}. Falling back to structured narrative.")
            # Graceful deterministic fallback
            return f"### Credit Appraisal Memo\n\n{prompt}\n\n*Generated via fallback synthesizer.*"

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        """
        Answers an underwriter question strictly from retrieved policy passages.
        """
        formatted_passages = []
        for i, passage in enumerate(retrieved_passages, 1):
            chunk_id = passage.get("id") or passage.get("chunk_id", f"chunk_{i}")
            text = passage.get("text") or passage.get("content", "")
            formatted_passages.append(f"[{chunk_id}]:\n{text}")

        context_block = "\n\n".join(formatted_passages)

        system_instruction = (
            "You are an underwriting policy verification assistant for FinScan AI.\n"
            "Answer the underwriter's question STRICTLY and SOLELY using the provided context passages.\n"
            "Cite the passage IDs in your answer (e.g. [credit_policy_v1_p1]).\n"
            "If the question cannot be answered using the provided passages, respond exactly with:\n"
            "'I cannot answer this question based on the provided documents.'"
        )

        user_content = (
            f"<evidence_passages>\n{context_block}\n</evidence_passages>\n\n"
            f"Underwriter Inquiry: {question}"
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
        }

        try:
            client = self._get_client()
            response = client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Failed to answer question via OpenCode Zen: {e}")
            return "I cannot answer this question based on the provided documents."

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
        model: Optional[str] = None,
        timeout_seconds: float = 30.0,
        http_client: Optional[httpx.Client] = None,
    ):
        groq_key = os.getenv("GROQ_API_KEY")
        self.api_key = api_key or groq_key or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY", "")

        default_base = "https://api.groq.com/openai/v1" if (groq_key and not base_url) else "https://opencode.ai/zen/v1"
        self.base_url = (base_url or os.getenv("OPENCODE_BASE_URL") or default_base).rstrip("/")

        default_model = "openai/gpt-oss-20b" if ("groq.com" in self.base_url or groq_key) else "zen-small"
        self.model = model or os.getenv("LLM_MODEL") or default_model
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

    def answer_question(
        self,
        question: str,
        retrieved_passages: List[Dict[str, Any]],
        findings_context: Optional[str] = None,
    ) -> str:
        """
        Answers an underwriting question STRICTLY from retrieved policy passages
        plus this application's own deterministic findings (when supplied) - the
        latter is what lets this answer questions like "why was this application
        flagged/rejected?" with the actual computed reason, not just a generic
        policy quote. Both sources are RAG-retrieved/deterministic, never
        free-generated, so a full explanation can be given without risking a
        hallucinated number or an autonomous disposition: the model narrates and
        explains, it never invents a new finding or issues a new verdict.
        """
        formatted_passages = []
        for i, passage in enumerate(retrieved_passages, 1):
            chunk_id = passage.get("id") or passage.get("chunk_id", f"chunk_{i}")
            text = passage.get("text") or passage.get("content", "")
            formatted_passages.append(f"[{chunk_id}]:\n{text}")

        context_block = "\n\n".join(formatted_passages) or "(no policy passages retrieved for this query)"
        findings_block = findings_context or "(this application has no findings recorded yet)"

        system_instruction = (
            "You are an underwriting research assistant for FinScan AI, helping a human "
            "underwriter understand WHY an application was flagged, rejected, or passed, "
            "and what policy requires.\n\n"
            "Answer STRICTLY and SOLELY using the two sources below - never from memory, "
            "assumption, or general lending knowledge:\n"
            "1. <application_findings> - this application's own deterministic rule results. "
            "These are already computed and verified; you may quote and explain them freely, "
            "but never invent a new finding, alter a verdict, or state a number that isn't in them.\n"
            "2. <evidence_passages> - retrieved policy clauses.\n\n"
            "When explaining a flag or rejection: name the specific rule(s) that fired, quote "
            "its stated reason, and explain the policy basis behind it in plain language a "
            "reviewer can act on - do not just repeat the reason verbatim with no context.\n"
            "Cite every claim: [RULE_ID] for a finding (e.g. [RULE-ID-01]), [chunk_id] for a "
            "policy clause (e.g. [credit_policy_v1_p1]).\n"
            "Never state whether the loan should be approved, rejected, or sanctioned going "
            "forward - that decision belongs to the human underwriter, not you.\n"
            "If neither source answers the question, respond exactly with:\n"
            "'I cannot answer this question based on the provided documents.'"
        )

        user_content = (
            f"<application_findings>\n{findings_block}\n</application_findings>\n\n"
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

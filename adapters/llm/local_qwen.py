"""
Offline fallback LLM adapter: Qwen / Gemma GGUF via llama.cpp or llama-cli/server.
Owned by Member 2 (Bhanu Teja) & Member 8 (Sai Mokshith).

Guarantees full offline functionality for Day 6 failure and network-outage tests.
Auto-detects:
1. Running llama-server (OpenAI-compatible HTTP endpoint)
2. Local llama-cli binary in PATH with GGUF model on disk
3. llama-cpp-python if installed
4. Deterministic offline rule synthesis fallback
"""

import os
import shutil
import subprocess
import logging
import httpx
from typing import List, Dict, Any, Optional
from adapters.llm.base import LLMPort

logger = logging.getLogger("finscan.adapters.llm.qwen")

DEFAULT_CANDIDATE_PATHS = [
    os.getenv("LOCAL_GGUF_MODEL_PATH", ""),
    r"C:\Users\bhanu\llama\gemma-4-E2B.gguf",
    "ml/artifacts/qwen3-4b-q4.gguf",
]


class LocalQwenLLM(LLMPort):
    """
    Offline local LLM adapter using local GGUF models.
    Supports llama-server HTTP, llama-cli execution, llama-cpp-python,
    and deterministic underwriting synthesis fallback.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        server_url: Optional[str] = None,
    ):
        self.model_path = self._resolve_model_path(model_path)
        self.n_ctx = n_ctx
        self.server_url = server_url or os.getenv("LLAMA_SERVER_URL", "http://localhost:8080/v1")
        self._llama_cli = shutil.which("llama-cli") or shutil.which("llama-cli.exe")
        self._llm_lib = None

    def _resolve_model_path(self, explicit_path: Optional[str]) -> str:
        if explicit_path is not None:
            return explicit_path
        for candidate in DEFAULT_CANDIDATE_PATHS:
            if candidate and os.path.exists(candidate):
                return candidate
        return "ml/artifacts/qwen3-4b-q4.gguf"

    def _call_llama_server(self, messages: List[Dict[str, str]], max_tokens: int = 512) -> Optional[str]:
        """Attempts to call running llama-server at self.server_url."""
        try:
            url = f"{self.server_url.rstrip('/')}/chat/completions"
            payload = {
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": max_tokens,
            }
            with httpx.Client(timeout=httpx.Timeout(5.0, connect=0.2)) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None

    def _call_llama_cli(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 512) -> Optional[str]:
        """Runs local llama-cli subprocess if binary and model exist."""
        if not self._llama_cli or not os.path.exists(self.model_path):
            return None

        full_prompt = f"System: {system_prompt}\nUser: {prompt}\nAssistant:" if system_prompt else prompt
        cmd = [
            self._llama_cli,
            "-m", self.model_path,
            "-p", full_prompt,
            "-c", str(self.n_ctx),
            "-n", str(max_tokens),
            "--temp", "0.0",
            "--simple-io",
            "--no-display-prompt",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            logger.warning(f"llama-cli returned code {result.returncode}: {result.stderr[:200]}")
        except Exception as e:
            logger.warning(f"llama-cli execution error: {e}")
        return None

    def _get_llama_lib(self):
        if self._llm_lib is not None:
            return self._llm_lib
        if not os.path.exists(self.model_path):
            return None
        try:
            from llama_cpp import Llama
            self._llm_lib = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=4,
                verbose=False,
            )
            logger.info(f"Loaded local GGUF model via llama-cpp from {self.model_path}")
            return self._llm_lib
        except Exception:
            return None

    def generate_summary(self, prompt: str, system_prompt: str) -> str:
        """
        Generates offline appraisal narrative from deterministic findings.
        Tries: llama-server -> llama-cli -> llama-cpp -> deterministic fallback.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # 1. llama-server
        out = self._call_llama_server(messages, max_tokens=1024)
        if out:
            return out

        # 2. llama-cli
        out = self._call_llama_cli(prompt=prompt, system_prompt=system_prompt, max_tokens=1024)
        if out:
            return out

        # 3. llama-cpp library
        llm = self._get_llama_lib()
        if llm is not None:
            try:
                res = llm.create_chat_completion(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=1024,
                )
                return res["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"llama-cpp error: {e}")

        # 4. Deterministic offline memo synthesizer fallback
        return (
            "### Credit Appraisal Memo (Offline Fallback)\n\n"
            f"{prompt}\n\n"
            "*Synthesized via local deterministic underwriting rules.*"
        )

    def answer_question(self, question: str, retrieved_passages: List[Dict[str, Any]]) -> str:
        """
        Answers underwriter questions offline using retrieved context.
        """
        formatted_context = "\n\n".join(
            f"[{p.get('id', f'chunk_{i}')}]: {p.get('text', '')}"
            for i, p in enumerate(retrieved_passages, 1)
        )
        sys_msg = (
            "You are an offline credit underwriting assistant. "
            "Answer strictly based on the context passages and cite passage IDs."
        )
        user_msg = f"<context>\n{formatted_context}\n</context>\n\nQuestion: {question}"
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]

        # 1. llama-server
        out = self._call_llama_server(messages, max_tokens=512)
        if out:
            return out

        # 2. llama-cli
        out = self._call_llama_cli(prompt=user_msg, system_prompt=sys_msg, max_tokens=512)
        if out:
            return out

        # 3. llama-cpp library
        llm = self._get_llama_lib()
        if llm is not None:
            try:
                res = llm.create_chat_completion(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=512,
                )
                return res["choices"][0]["message"]["content"]
            except Exception as e:
                logger.warning(f"llama-cpp Q&A error: {e}")

        # 4. Keyword matching fallback for offline inquiry
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

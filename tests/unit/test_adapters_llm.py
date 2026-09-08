"""
Unit tests for OpenCodeZenLLM and LocalQwenLLM adapters.
Owned by Member 2 (Bhanu Teja) & Member 8 (Sai Mokshith).

Verifies:
- OpenCodeZenLLM: prompt injection isolation, chat completions payload, Q&A citations, and graceful fallback.
- LocalQwenLLM: offline deterministic narrative synthesis, keyword matching Q&A, and mock model invocation.
"""

from unittest.mock import MagicMock
import pytest
from adapters.llm.opencode import OpenCodeZenLLM
from adapters.llm.local_qwen import LocalQwenLLM


# =====================================================================
# OpenCodeZenLLM Tests
# =====================================================================

def test_opencode_generate_summary_success():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "### Credit Appraisal Memo\nAll credit rules passed with high confidence."}}
        ]
    }
    mock_client.post.return_value = mock_response

    llm = OpenCodeZenLLM(api_key="test-key", http_client=mock_client)
    result = llm.generate_summary("RULE-COMP-01: PASS", "System prompt instructions")

    assert "Credit Appraisal Memo" in result
    mock_client.post.assert_called_once()
    payload = mock_client.post.call_args[1]["json"]
    user_prompt = payload["messages"][1]["content"]
    # Verify prompt injection isolation delimiters
    assert "<context_data>" in user_prompt
    assert "</context_data>" in user_prompt
    assert "RULE-COMP-01: PASS" in user_prompt


def test_opencode_generate_summary_fallback_on_error():
    mock_client = MagicMock()
    mock_client.post.side_effect = RuntimeError("Network connection failed")

    llm = OpenCodeZenLLM(api_key="test-key", http_client=mock_client)
    result = llm.generate_summary("RULE-INC-01: PASS", "System prompt instructions")

    # Should gracefully return deterministic fallback without crashing
    assert "Credit Appraisal Memo" in result
    assert "RULE-INC-01: PASS" in result
    assert "fallback synthesizer" in result


def test_opencode_answer_question_with_citations():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "According to [credit_policy_v1_p1], max DTI allowed is 45%."}}
        ]
    }
    mock_client.post.return_value = mock_response

    llm = OpenCodeZenLLM(api_key="test-key", http_client=mock_client)
    passages = [
        {"id": "credit_policy_v1_p1", "text": "Debt-to-income ratio must not exceed 45% for prime loans."}
    ]

    answer = llm.answer_question("What is the maximum allowable DTI?", passages)

    assert "credit_policy_v1_p1" in answer
    payload = mock_client.post.call_args[1]["json"]
    user_prompt = payload["messages"][1]["content"]
    assert "<evidence_passages>" in user_prompt
    assert "[credit_policy_v1_p1]" in user_prompt


# =====================================================================
# LocalQwenLLM Tests
# =====================================================================

def test_local_qwen_offline_summary_fallback():
    # Without model on disk, should execute deterministic synthesis
    llm = LocalQwenLLM(model_path="ml/artifacts/nonexistent_model.gguf")
    result = llm.generate_summary("Net salary verified at INR 50,000", "System prompt")

    assert "Credit Appraisal Memo" in result
    assert "Net salary verified at INR 50,000" in result
    assert "deterministic underwriting rules" in result


def test_local_qwen_offline_answer_question_keyword_match():
    llm = LocalQwenLLM(model_path="ml/artifacts/nonexistent_model.gguf")
    passages = [
        {"id": "kyc_guidelines_v1_p1", "text": "PAN card proof is strictly mandatory for all loan applications."},
        {"id": "credit_policy_v1_p2", "text": "Minimum monthly net salary required is INR 25,000."},
    ]

    answer = llm.answer_question("What are the PAN card requirements?", passages)

    assert "kyc_guidelines_v1_p1" in answer
    assert "PAN card" in answer


def test_local_qwen_offline_answer_question_unanswerable():
    llm = LocalQwenLLM(model_path="ml/artifacts/nonexistent_model.gguf")
    passages = [
        {"id": "policy_doc", "text": "General bank terms and conditions."}
    ]

    answer = llm.answer_question("What is the weather in Paris?", passages)
    assert "I cannot answer this question based on the provided documents." in answer

"""
Tests for the experimental tool-calling Q&A agent (apps/api/agent.py).

Per AGENTS.md, CI must never execute paid cloud API calls - every test here
mocks langgraph.prebuilt.create_react_agent (and the chat model, where used)
rather than hitting a live Groq/OpenAI endpoint.
"""

import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import apps.api.agent as agent_module


def test_get_agentic_chat_model_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    assert agent_module.get_agentic_chat_model() is None


def test_get_agentic_chat_model_builds_client_with_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_not_real")
    model = agent_module.get_agentic_chat_model()
    assert model is not None
    assert model.model_name == "openai/gpt-oss-20b"


def test_answer_question_agentic_returns_none_when_no_llm(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    fake_retriever = MagicMock()
    result = agent_module.answer_question_agentic("What is the DTI policy?", fake_retriever)
    assert result is None


def test_answer_question_agentic_grounds_answer_and_collects_citations(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_not_real")

    fake_retriever = MagicMock()
    fake_retriever.retrieve_policy.return_value = [
        {"chunk_id": "credit_policy_v1_p2", "text": "DTI must not exceed 45%.", "score": 0.9, "is_policy": True}
    ]

    def fake_create_react_agent(chat_model, tools, prompt=None):
        class FakeAgent:
            def invoke(self, payload, config=None):
                query = payload["messages"][0][1]
                # Round-trip through the real tool closure, exactly like a real
                # ReAct step would, so session_hits gets populated for real.
                tool_output = tools[0].invoke({"query": query})
                match = re.search(r"\[([\w\-]+)\]", tool_output)
                chunk_id = match.group(1) if match else "UNKNOWN"
                answer = f"The maximum allowed DTI is 45% [{chunk_id}]."
                return {"messages": [SimpleNamespace(content=answer)]}

        return FakeAgent()

    monkeypatch.setattr("langgraph.prebuilt.create_react_agent", fake_create_react_agent)

    result = agent_module.answer_question_agentic("What is the max DTI?", fake_retriever)

    assert result is not None
    assert "credit_policy_v1_p2" in result["answer"]
    assert "UNGROUNDED CLAIM DROPPED" not in result["answer"]
    assert result["chunk_ids"] == ["credit_policy_v1_p2"]
    assert len(result["citations"]) == 1
    fake_retriever.retrieve_policy.assert_called_once()


def test_answer_question_agentic_strips_unauthorized_citation(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_not_real")

    fake_retriever = MagicMock()
    fake_retriever.retrieve_policy.return_value = [
        {"chunk_id": "credit_policy_v1_p2", "text": "DTI must not exceed 45%.", "score": 0.9, "is_policy": True}
    ]

    def fake_create_react_agent(chat_model, tools, prompt=None):
        class FakeAgent:
            def invoke(self, payload, config=None):
                # Simulate the tool being called (populates session_hits)...
                tools[0].invoke({"query": "dti"})
                # ...but the model hallucinates a citation it was never given.
                answer = "The max DTI is 60% [fabricated_chunk_id]."
                return {"messages": [SimpleNamespace(content=answer)]}

        return FakeAgent()

    monkeypatch.setattr("langgraph.prebuilt.create_react_agent", fake_create_react_agent)

    result = agent_module.answer_question_agentic("What is the max DTI?", fake_retriever)

    assert result is not None
    # The fabricated claim's content itself must not survive - only the
    # sanitizer's own warning (which names the rejected id) is expected here.
    assert "60%" not in result["answer"]
    assert "UNGROUNDED CLAIM DROPPED" in result["answer"]


def test_answer_question_agentic_redacts_disposition_language(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_not_real")

    fake_retriever = MagicMock()
    fake_retriever.retrieve_policy.return_value = [
        {"chunk_id": "credit_policy_v1_p2", "text": "DTI must not exceed 45%.", "score": 0.9, "is_policy": True}
    ]

    def fake_create_react_agent(chat_model, tools, prompt=None):
        class FakeAgent:
            def invoke(self, payload, config=None):
                tools[0].invoke({"query": "dti"})
                answer = "Based on this, the loan is approved [credit_policy_v1_p2]."
                return {"messages": [SimpleNamespace(content=answer)]}

        return FakeAgent()

    monkeypatch.setattr("langgraph.prebuilt.create_react_agent", fake_create_react_agent)

    result = agent_module.answer_question_agentic("Should this be approved?", fake_retriever)

    assert result is not None
    assert "ABSTENTION" in result["answer"]
    # The original disposition claim must not survive redaction (the safety
    # message itself legitimately names "approve" while explaining the
    # redaction, so assert on the specific claim text, not the bare pattern).
    assert "the loan is approved" not in result["answer"]


def test_answer_question_agentic_falls_back_to_none_on_agent_exception(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key_not_real")

    fake_retriever = MagicMock()

    def fake_create_react_agent(chat_model, tools, prompt=None):
        class FakeAgent:
            def invoke(self, payload, config=None):
                raise RuntimeError("simulated upstream failure")

        return FakeAgent()

    monkeypatch.setattr("langgraph.prebuilt.create_react_agent", fake_create_react_agent)

    result = agent_module.answer_question_agentic("Anything?", fake_retriever)
    assert result is None

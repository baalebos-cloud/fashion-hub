"""Reasoning models get room to think, and their thinking never ends up in the answer."""
import json

from app.core.config import settings
from app.integrations.ai.llm_client import ChatMessage, LLMClient, groq_length_settings, strip_reasoning


def test_length_settings_per_model():
    assert groq_length_settings("llama-3.1-8b-instant", 200) == {"max_tokens": 200}
    assert groq_length_settings("openai/gpt-oss-120b", 200) == {"max_completion_tokens": 1736, "reasoning_effort": "low"}
    assert groq_length_settings("qwen/qwen3.8-27b", 600) == {"max_completion_tokens": 2136, "reasoning_format": "hidden"}


def test_thinking_is_removed_from_answers():
    assert strip_reasoning('<think>let me see\nhmm</think>\n{"a": 1}') == '{"a": 1}'
    assert strip_reasoning("plain answer") == "plain answer"


def test_short_requests_still_get_an_answer(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test")
    monkeypatch.setattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
    sent = {}

    class Reply:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": '{"category": "agbada"}'}}]}

    import app.integrations.ai.llm_client as module
    monkeypatch.setattr(module.httpx, "post", lambda url, **kw: sent.update(kw) or Reply())
    result = LLMClient()._complete_groq([ChatMessage(role="user", content="find agbada")], 200)
    assert json.loads(result.content) == {"category": "agbada"}
    assert sent["json"]["max_completion_tokens"] == 1736 and "max_tokens" not in sent["json"]
    assert sent["json"]["reasoning_effort"] == "low"

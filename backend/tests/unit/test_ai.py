"""Unit tests for AI navigation-assistant scoping (role-appropriate app map
injection). Mocks the LLM client so no real API call is made."""
from unittest.mock import MagicMock

from app.integrations.ai.llm_client import ChatCompletionResult
from app.integrations.ai.navigation_agent import build_navigation_response


def test_navigation_response_only_uses_role_scoped_app_map():
    fake_client = MagicMock()
    fake_client.complete.return_value = ChatCompletionResult(content="Open Orders, then Track Delivery.", raw_response={})

    answer = build_navigation_response(user_role="customer", user_question="Where can I track my order?", llm_client=fake_client)

    assert "Track Delivery" in answer
    # Confirm the system message passed to the model only contains
    # customer-scoped routes, not admin-only ones.
    system_messages = [m.content for m in fake_client.complete.call_args[0][0] if m.role == "system"]
    combined = "\n".join(system_messages)
    assert "/admin" not in combined

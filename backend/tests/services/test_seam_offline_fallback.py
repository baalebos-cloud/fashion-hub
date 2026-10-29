"""Seam returns honest navigation advice when Vertex inference is unavailable."""
from unittest.mock import MagicMock, patch

from app.services.ai_service import AIService
from app.services.vertex_service import VertexUnavailable


def test_navigation_falls_back_when_vertex_fails(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "VERTEX_AI_ENABLED", True)

    conversation = MagicMock()
    conversation.id = "conversation-id"
    conversation.user_id = "user-id"
    db = MagicMock()
    db.get.return_value = conversation

    class Messages:
        @staticmethod
        def list_messages(_):
            return [MagicMock(role="user", content="How do I accept an order?")]

    with patch("app.repositories.user_repository.UserRepository.get_by_id",
               return_value=MagicMock(role="tailor")), \
         patch("app.repositories.ai_repository.AIRepository.list_messages",
               side_effect=Messages.list_messages), \
         patch("app.services.vertex_service.get_vertex_service") as provider:
        provider.return_value.ask_seam.side_effect = VertexUnavailable("service unavailable")
        result = AIService(db).send_message(
            conversation_id="conversation-id", user_id="user-id",
            content="How do I accept an order?",
        )
    assert "offline assistance mode" in result["answer"]
    assert result["conversation_id"] == "conversation-id"

"""
Thin wrapper around the configured AI provider's chat completion API.
Isolating this here means ai_service.py never imports an SDK directly, so
switching AI_PROVIDER doesn't ripple through business logic.
"""
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import ExternalProviderError


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class ChatCompletionResult:
    content: str
    raw_response: dict


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL

    def complete(self, messages: list[ChatMessage], max_tokens: int = 512) -> ChatCompletionResult:
        if settings.AI_PROVIDER == "anthropic":
            return self._complete_anthropic(messages, max_tokens)
        raise ExternalProviderError(f"Unsupported AI_PROVIDER '{settings.AI_PROVIDER}'")

    def _complete_anthropic(self, messages: list[ChatMessage], max_tokens: int) -> ChatCompletionResult:
        try:
            import anthropic
        except ImportError as exc:
            raise ExternalProviderError("The 'anthropic' package is not installed.") from exc

        system_messages = [m.content for m in messages if m.role == "system"]
        conversation = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        try:
            # Omit the optional system field when absent: JSON null is not
            # a valid system prompt. The context manager closes the SDK's
            # HTTP transport on both successful and failed requests.
            request = dict(model=self.model, max_tokens=max_tokens, messages=conversation)
            if system_messages:
                request["system"] = "\n".join(system_messages)
            with anthropic.Anthropic(api_key=self.api_key) as client:
                response = client.messages.create(**request)
        except Exception as exc:  # noqa: BLE001 - provider SDK exception types vary
            raise ExternalProviderError("AI provider request failed. Please try again.") from exc

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return ChatCompletionResult(content=text, raw_response=response.model_dump())

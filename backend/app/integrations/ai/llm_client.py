"""Provider-isolated chat completions for Seam."""
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatCompletionResult:
    content: str
    raw_response: dict


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else settings.AI_API_KEY
        # Distinct API key: n8n or Anthropic secrets must never be passed to Google.
        self.vertex_api_key = api_key if api_key is not None else settings.VERTEX_AI_API_KEY
        self.model = model or settings.AI_MODEL

    def complete(self, messages: list[ChatMessage], max_tokens: int = 512) -> ChatCompletionResult:
        if settings.AI_PROVIDER == "anthropic":
            return self._complete_anthropic(messages, max_tokens)
        if settings.AI_PROVIDER in {"vertex_ai", "vertexai"}:
            return self._complete_vertex_ai(messages, max_tokens)
        raise ExternalProviderError("Seam has an unsupported AI provider configured.")

    def _complete_vertex_ai(self, messages: list[ChatMessage], max_tokens: int) -> ChatCompletionResult:
        """Google Cloud Vertex AI express-mode API, not the separate Gemini Developer API."""
        if not self.vertex_api_key:
            raise ExternalProviderError("Seam's Vertex AI credentials are not configured.")
        if not re.fullmatch(r"gemini-[a-zA-Z0-9][a-zA-Z0-9.-]{0,80}", self.model):
            raise ExternalProviderError("Choose a supported Gemini model for Seam's Vertex AI provider.")
        if not 1 <= max_tokens <= 4096:
            raise ExternalProviderError("Invalid AI response length.")
        system = "\n".join(m.content for m in messages if m.role == "system")
        contents = [
            {"role": "model" if m.role == "assistant" else "user",
             "parts": [{"text": m.content}]}
            for m in messages if m.role in {"user", "assistant"} and m.content
        ]
        if not contents or contents[-1]["role"] != "user":
            raise ExternalProviderError("Seam requires a user message.")
        generation_config = {"maxOutputTokens": max(max_tokens, 1024), "temperature": 0.2}
        # Gemini 3 normally uses HIGH thinking, which can exhaust 512 tokens.
        if self.model.startswith("gemini-3"):
            generation_config["thinkingConfig"] = {"thinkingLevel": "LOW"}
        payload = {"contents": contents, "generationConfig": generation_config}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        # Fixed Google API origin and strictly constrained model path prevent SSRF.
        url = (
            "https://aiplatform.googleapis.com/v1/publishers/google/models/"
            + self.model + ":generateContent"
        )
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self.vertex_api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=20.0,
            )
        except httpx.RequestError:
            raise ExternalProviderError("Vertex AI is currently unreachable. Please retry.") from None
        if response.status_code not in {200, 201}:
            # Provider bodies may contain personal data and must never be sent to clients.
            raise ExternalProviderError(f"Vertex AI request failed (HTTP {response.status_code}).")
        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            answer = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
        except (ValueError, TypeError, IndexError, KeyError, AttributeError):
            raise ExternalProviderError("Vertex AI returned an invalid response.") from None
        if not answer:
            raise ExternalProviderError("Vertex AI did not return an answer.")
        return ChatCompletionResult(content=answer, raw_response=data)

    def _complete_anthropic(self, messages: list[ChatMessage], max_tokens: int) -> ChatCompletionResult:
        try:
            import anthropic
        except ImportError as exc:
            raise ExternalProviderError("The 'anthropic' package is not installed.") from exc
        system_messages = [m.content for m in messages if m.role == "system"]
        conversation = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        try:
            request = dict(model=self.model, max_tokens=max_tokens, messages=conversation)
            if system_messages:
                request["system"] = "\n".join(system_messages)
            with anthropic.Anthropic(api_key=self.api_key) as client:
                response = client.messages.create(**request)
        except Exception as exc:
            raise ExternalProviderError("AI provider request failed. Please try again.") from exc
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return ChatCompletionResult(content=text, raw_response=response.model_dump())

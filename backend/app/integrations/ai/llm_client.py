"""Provider-isolated chat completions for Seam."""
import re
from app.core.logging import get_logger
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatCompletionResult:
    content: str
    raw_response: dict


# Reasoning models (gpt-oss, Qwen 3) spend part of the length allowance thinking before they answer.
# Give them room for that on top of the answer's own limit, and keep gpt-oss's thinking short.
REASONING_MODEL_PREFIXES = ("openai/gpt-oss", "qwen/qwen3")
REASONING_TOKENS = 1536


def groq_length_settings(model: str, answer_tokens: int) -> dict:
    if not model.startswith(REASONING_MODEL_PREFIXES):
        return {"max_tokens": answer_tokens}
    # gpt-oss: keep thinking short (its thinking never appears in the answer text). Qwen 3: keep the
    # thinking out of the answer text, which JSON replies need.
    extra = ({"reasoning_effort": "low"} if model.startswith("openai/gpt-oss")
             else {"reasoning_format": "hidden"})
    return {"max_completion_tokens": answer_tokens + REASONING_TOKENS, **extra}


def strip_reasoning(text: str) -> str:
    """Remove a <think>…</think> block some models put before their answer."""
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


class LLMClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float | None = None):
        self.api_key = api_key if api_key is not None else settings.AI_API_KEY
        # Distinct API key: n8n or Anthropic secrets must never be passed to Google.
        self.vertex_api_key = api_key if api_key is not None else settings.VERTEX_AI_API_KEY
        self.model = model or settings.AI_MODEL
        self.timeout = timeout  # seconds; None keeps each provider's default

    def complete(self, messages: list[ChatMessage], max_tokens: int = 512) -> ChatCompletionResult:
        provider = settings.AI_PROVIDER.lower()
        try:
            if provider == "anthropic":
                return self._complete_anthropic(messages, max_tokens)
            if provider in {"vertex_ai", "vertexai"}:
                return self._complete_vertex_ai(messages, max_tokens)
            if provider == "groq":
                return self._complete_groq(messages, max_tokens)
            raise ExternalProviderError("Seam has an unsupported AI provider configured.")
        except ExternalProviderError:
            if (provider in {"vertex_ai", "vertexai"}
                    and settings.AI_FALLBACK_PROVIDER == "groq"
                    and settings.GROQ_API_KEY):
                logger.warning("seam_primary_ai_failed_using_groq_fallback")
                return self._complete_groq(messages, max_tokens)
            raise

    def _complete_groq(self, messages: list[ChatMessage], max_tokens: int) -> ChatCompletionResult:
        """Groq text completions. Keep authentication strictly server-side."""
        if not settings.GROQ_API_KEY:
            raise ExternalProviderError("Groq API credentials are not configured.")
        if not 1 <= max_tokens <= 4096:
            raise ExternalProviderError("Invalid AI response length.")
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": msg.role, "content": msg.content}
                         for msg in messages if msg.role in {"system", "user", "assistant"}],
            "temperature": 0.2,
            **groq_length_settings(settings.GROQ_MODEL, max_tokens),
        }
        if not payload["messages"]:
            raise ExternalProviderError("Seam requires a message.")
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json=payload, timeout=self.timeout or 20.0,
            )
        except httpx.RequestError:
            logger.warning("seam_groq_transport_failure")
            raise ExternalProviderError("Groq is currently unreachable.") from None
        if response.status_code != 200:
            logger.warning("seam_groq_api_failure", extra={"status": response.status_code})
            raise ExternalProviderError(f"Groq request failed (HTTP {response.status_code}).")
        try:
            data = response.json()
            answer = strip_reasoning(data["choices"][0]["message"]["content"])
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("empty")
        except (ValueError, KeyError, IndexError, TypeError):
            raise ExternalProviderError("Groq returned an invalid response.") from None
        return ChatCompletionResult(content=answer.strip(), raw_response=data)

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
        generation_config = {"maxOutputTokens": max(max_tokens, 1024)}
        # Gemini 3 defaults to HIGH reasoning, potentially consuming the
        # entire response budget. Google's recommended temperature is 1.0.
        if self.model.startswith("gemini-3"):
            generation_config["thinkingConfig"] = {"thinkingLevel": "LOW"}
        else:
            generation_config["temperature"] = 0.2
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
                timeout=self.timeout or 20.0,
            )
        except httpx.RequestError as exc:
            logger.warning("seam_vertex_transport_failure", extra={
                "provider": "vertex_ai", "error_type": type(exc).__name__,
            })
            raise ExternalProviderError("Vertex AI is currently unreachable. Please retry.") from None
        if response.status_code not in {200, 201}:
            # Never log provider response bodies, headers, keys or user prompts.
            allowed = {
                "INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED",
                "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "NOT_FOUND",
                "UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL",
            }
            try:
                code = response.json().get("error", {}).get("status")
            except (ValueError, TypeError, AttributeError):
                code = None
            logger.warning("seam_vertex_api_failure", extra={
                "provider": "vertex_ai",
                "http_status": response.status_code,
                "provider_code": code if code in allowed else "UNKNOWN",
            })
            raise ExternalProviderError(f"Vertex AI request failed (HTTP {response.status_code}).")
        try:
            data = response.json()
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]
            answer = "".join(
                p.get("text", "") for p in parts
                if isinstance(p, dict) and not p.get("thought", False)
            ).strip()
        except (ValueError, TypeError, IndexError, KeyError, AttributeError):
            logger.warning("seam_vertex_invalid_response", extra={"provider": "vertex_ai"})
            raise ExternalProviderError("Vertex AI returned an invalid response.") from None
        if not answer:
            reason = str(candidate.get("finishReason", ""))
            reason = reason if reason in {
                "MAX_TOKENS", "STOP", "SAFETY", "RECITATION", "OTHER",
            } else "UNKNOWN"
            logger.warning("seam_vertex_empty_response", extra={
                "provider": "vertex_ai", "finish_reason": reason,
            })
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
            options = {"timeout": self.timeout} if self.timeout else {}
            with anthropic.Anthropic(api_key=self.api_key, **options) as client:
                response = client.messages.create(**request)
        except Exception as exc:
            raise ExternalProviderError("AI provider request failed. Please try again.") from exc
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        return ChatCompletionResult(content=text, raw_response=response.model_dump())

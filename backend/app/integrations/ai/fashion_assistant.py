"""AI helper that turns a free-text style request into structured search
filters used by search_service (garment type, style tags, budget range)."""
import json

from app.integrations.ai.llm_client import ChatMessage, LLMClient
from app.integrations.ai.prompts import FASHION_ASSISTANT_SYSTEM_PROMPT


def extract_search_filters(*, user_query: str, llm_client: LLMClient | None = None) -> dict:
    llm_client = llm_client or LLMClient()
    messages = [
        ChatMessage(role="system", content=FASHION_ASSISTANT_SYSTEM_PROMPT),
        ChatMessage(
            role="system",
            content=(
                "Respond ONLY with JSON: "
                '{"garment_type": str|null, "style_tags": [str], "budget_min": number|null, "budget_max": number|null}'
            ),
        ),
        ChatMessage(role="user", content=user_query),
    ]
    result = llm_client.complete(messages, max_tokens=256)
    try:
        return json.loads(result.content)
    except json.JSONDecodeError:
        return {"garment_type": None, "style_tags": [], "budget_min": None, "budget_max": None}

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


def request_search_filters(user_query: str, llm_client: LLMClient | None = None) -> str:
    """Raw AI reply for smart search; services/smart_search_service.py validates it. The query
    has already had emails and phone numbers removed, and nothing else about the shopper is sent."""
    llm_client = llm_client or LLMClient()
    messages = [
        ChatMessage(role="system", content=FASHION_ASSISTANT_SYSTEM_PROMPT),
        ChatMessage(role="system", content=(
            "Turn the shopper's request into search filters for Nigerian tailoring designs. "
            "Respond ONLY with JSON: "
            '{"garment_type": str|null, "style_tags": [str], "budget_min": number|null, "budget_max": number|null}. '
            "Amounts are in naira (50k = 50000). Use short plain words (e.g. agbada, kaftan, lace, blue). "
            "Never name products, tailors or prices that weren't in the request."
        )),
        ChatMessage(role="user", content=user_query),
    ]
    return llm_client.complete(messages, max_tokens=200).content

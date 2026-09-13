"""
Builds the navigation-assistant response: injects only role-appropriate app
map context (pages/actions available to THIS user's role) into the prompt,
so the model can't hallucinate admin-only routes for a customer, etc.
"""
from app.integrations.ai.llm_client import ChatMessage, LLMClient
from app.integrations.ai.prompts import NAVIGATION_ASSISTANT_SYSTEM_PROMPT

# Minimal static app map; expand as routes are added. Keeping this explicit
# (rather than having the model infer routes) is what prevents incorrect
# navigation instructions.
ROLE_APP_MAP = {
    "customer": {
        "Find a Tailor": "/discover/professionals",
        "Orders": "/orders",
        "Track Delivery": "/orders/:id/tracking",
        "Invoices": "/orders/:id/invoice",
        "Measurements": "/profile/measurements",
        "Favorites": "/favorites",
    },
    "tailor": {
        "Incoming Orders": "/professional/orders",
        "Vendor Marketplace": "/vendor-marketplace",
        "Cart": "/vendor-marketplace/cart",
        "Portfolio": "/professional/portfolio",
        "KYC/KYB": "/professional/verification",
    },
    "designer": {
        "Incoming Orders": "/professional/orders",
        "Portfolio": "/professional/portfolio",
        "KYC/KYB": "/professional/verification",
    },
    "vendor": {
        "Products": "/vendor/products",
        "Orders": "/vendor/orders",
        "Inventory": "/vendor/inventory",
    },
    "delivery_partner": {
        "Delivery Requests": "/delivery/requests",
        "Active Deliveries": "/delivery/active",
    },
}


def build_navigation_response(*, user_role: str, user_question: str, llm_client: LLMClient | None = None) -> str:
    llm_client = llm_client or LLMClient()
    app_map = ROLE_APP_MAP.get(user_role, {})
    app_map_text = "\n".join(f"- {name}: {route}" for name, route in app_map.items())

    messages = [
        ChatMessage(role="system", content=NAVIGATION_ASSISTANT_SYSTEM_PROMPT),
        ChatMessage(
            role="system",
            content=f"Pages/routes available to this user (role={user_role}):\n{app_map_text}",
        ),
        ChatMessage(role="user", content=user_question),
    ]
    result = llm_client.complete(messages)
    return result.content

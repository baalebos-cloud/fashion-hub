"""
Builds the navigation-assistant response: injects only role-appropriate app
map context (pages/actions available to THIS user's role) into the prompt,
so the model can't hallucinate admin-only routes for a customer, etc.
"""
from app.core.exceptions import ExternalProviderError
from app.integrations.ai.llm_client import ChatMessage, LLMClient
from app.integrations.ai.prompts import NAVIGATION_ASSISTANT_SYSTEM_PROMPT

# Minimal static app map; expand as routes are added. Keeping this explicit
# (rather than having the model infer routes) is what prevents incorrect
# navigation instructions.
ROLE_APP_MAP = {
    "customer": {
        "Find a Tailor": "/app/customer/find",
        "Orders": "/app/customer/orders",
        "Track Delivery": "/app/customer/orders/:id/track",
        "Invoices": "/app/customer/invoices",
        "Measurements": "/app/customer/measurements",
        "Favorites": "/app/customer/favorites",
    },
    "tailor": {
        "Incoming Orders": "/app/professional/orders",
        "Vendor Marketplace": "/app/professional/vendor-marketplace",
        "Cart": "/app/professional/cart",
        "Portfolio": "/app/professional/portfolio",
        "KYC/KYB": "/app/professional/verification",
    },
    "designer": {
        "Incoming Orders": "/app/professional/orders",
        "Portfolio": "/app/professional/portfolio",
        "KYC/KYB": "/app/professional/verification",
    },
    "vendor": {
        "Products": "/app/vendor/products",
        "Orders": "/app/vendor/orders",
        "Inventory": "/app/vendor/inventory",
    },
    "delivery_partner": {
        "Delivery Requests": "/app/delivery/requests",
        "Active Deliveries": "/app/delivery/active",
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
    try:
        result = llm_client.complete(messages)
        return result.content
    except ExternalProviderError:
        # Answer only from this role's fixed navigation map during outages;
        # never guess order status, promise actions, or leak provider details.
        question = user_question.casefold()
        if any(phrase in question for phrase in (
            "what can you do", "what can you so", "your capabilities", "how can you help",
        )):
            if user_role in {"tailor", "designer"}:
                scope = "I can guide you through incoming orders, materials, your portfolio, and verification."
            elif user_role == "vendor":
                scope = "I can help locate products, inventory, and your received orders."
            elif user_role == "customer":
                scope = "I can help find tailors, orders, delivery tracking, measurements, and favorites."
            elif user_role == "delivery_partner":
                scope = "I can guide you to delivery requests and active deliveries."
            else:
                scope = "I can help navigate the available Fashion Hub pages."
            return (
                scope + " I do not accept orders, update deliveries, approve accounts "
                "or move payments on your behalf. Live Gemini answers are temporarily unavailable."
            )
        if user_role in {"tailor", "designer"}:
            if "verif" in question or "kyc" in question or "kyb" in question:
                return (
                    "Open Verification (/app/professional/verification) to check "
                    "the identity-verification instructions and available status. "
                    "Identity verification and business verification are separate. "
                    "The business-verification (KYB) API is not fully implemented, "
                    "so do not assume that submitting the screen completes approval. "
                    "Contact support if you need an official verification decision."
                )
            if any(term in question for term in (
                "material", "fabric", "supplier", "marketplace"
            )):
                if user_role == "designer":
                    return (
                        "Material shopping routes are not currently confirmed for "
                        "the designer role. Use your visible navigation or contact "
                        "support rather than following an unverified link."
                    )
                return (
                    "Open Vendor Marketplace (/app/professional/vendor-marketplace) "
                    "to browse available materials. Select a product to review its "
                    "details, then add it to your cart if that option is available. "
                    "Open Cart (/app/professional/cart) to review your selections "
                    "before proceeding with any supported checkout steps. "
                    "Availability and purchases are not confirmed by Seam."
                )
            if "portfolio" in question:
                return (
                    "Open Portfolio (/app/professional/portfolio) to manage "
                    "the work samples and details available in your account. "
                    "Seam cannot publish or edit portfolio entries for you."
                )
        if user_role in {"tailor", "designer"} and "accept" in question and "order" in question:
            return (
                "Seam's AI connection is temporarily unavailable. "
                "Open Incoming Orders (/app/professional/orders), select your pending "
                "customer order, then choose Accept if available. "
                "Only eligible orders assigned to you can be accepted."
            )
        if user_role == "vendor" and "order" in question:
            return (
                "Seam's AI connection is temporarily unavailable. "
                "Open Orders (/app/vendor/orders), select an order, "
                "and review its available fulfillment actions."
            )
        if user_role == "customer" and "order" in question:
            return (
                "Seam's AI connection is temporarily unavailable. "
                "Open Orders (/app/customer/orders) to review or track your orders."
            )
        pages = list(app_map.items())[:3]
        directory = "; ".join(f"{name}: {route}" for name, route in pages)
        return (
            "Seam's AI connection is temporarily unavailable. "
            + (f"You can still use these pages: {directory}." if directory
               else "Please use the navigation menu or contact support.")
        )

"""Isolated Interswitch sandbox checkout readiness, no transaction or secret exposure."""
from urllib.parse import urlsplit

from app.core.config import settings


def sandbox_readiness() -> dict:
    callback = f"{settings.APP_URL.rstrip('/')}{settings.API_PREFIX}/interswitch/return"
    parsed = urlsplit(callback)
    checks = {
        "non_production_environment": not settings.is_production,
        "sandbox_enabled": bool(settings.INTERSWITCH_SANDBOX_ENABLED),
        "merchant_code_configured": bool(settings.INTERSWITCH_MERCHANT_CODE),
        "pay_item_id_configured": bool(settings.INTERSWITCH_PAY_ITEM_ID),
        "https_callback": parsed.scheme == "https" and bool(parsed.netloc)
            and not parsed.username and not parsed.password,
    }
    return {"ready": all(checks.values()), "mode": "sandbox", "checks": checks}

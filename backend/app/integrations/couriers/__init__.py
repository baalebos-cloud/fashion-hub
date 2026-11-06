"""External courier companies behind one contract (logistics phase 6).

Only couriers listed in EXTERNAL_COURIERS are offered. The built-in "sandbox" courier is for
development and tests and is refused in production. Real adapters (e.g. Shipbubble, Sendbox,
GIG) are added here once their API access and credentials are confirmed.
"""
from app.core.config import settings
from app.integrations.couriers.base import CourierAdapter
from app.integrations.couriers.sandbox import SandboxCourier

_ADAPTERS = {"sandbox": SandboxCourier}


def enabled_couriers() -> dict[str, CourierAdapter]:
    names = [n for n in settings.EXTERNAL_COURIERS if n in _ADAPTERS]
    if settings.APP_ENV == "production":
        names = [n for n in names if n != "sandbox"]
    return {name: _ADAPTERS[name]() for name in names}


def get_courier(name: str) -> CourierAdapter | None:
    return enabled_couriers().get(name)

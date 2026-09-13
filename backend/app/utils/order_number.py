"""Human-readable, sortable order number generation (e.g. CO-20260912-A1B2C3)."""
import secrets
from datetime import datetime, timezone


def generate_order_number(prefix: str = "CO") -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()
    return f"{prefix}-{date_part}-{random_part}"

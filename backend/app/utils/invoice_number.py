"""Sequential-looking, collision-resistant invoice number generation."""
import secrets
from datetime import datetime, timezone


def generate_invoice_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"INV-{date_part}-{random_part}"


def generate_receipt_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"RCT-{date_part}-{random_part}"

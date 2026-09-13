"""Currency formatting/rounding helpers. Monetary values are stored as
Numeric(12,2) in Postgres and as Python floats in the application layer for
this scaffold -- consider `decimal.Decimal` end-to-end in production to
avoid floating-point rounding drift on financial totals."""
from decimal import ROUND_HALF_UP, Decimal


def round_currency(amount: float) -> float:
    return float(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_currency(amount: float, currency: str = "NGN") -> str:
    symbols = {"NGN": "₦", "USD": "$", "GBP": "£", "EUR": "€"}
    symbol = symbols.get(currency, currency + " ")
    return f"{symbol}{amount:,.2f}"

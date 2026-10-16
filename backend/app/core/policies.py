"""Pure security policies shared by validation and service boundaries."""
from decimal import Decimal, InvalidOperation

PUBLIC_SIGNUP_ROLES = frozenset({"customer", "tailor", "designer", "vendor", "delivery_partner"})


def validate_payment_identity(*, expected_reference, reference, expected_amount, amount,
                              expected_currency, currency) -> None:
    """Reject incorrect settlements before mutating any payment/order state."""
    if not reference or reference != expected_reference:
        raise ValueError("Payment reference does not match")
    if not currency or currency != expected_currency:
        raise ValueError("Payment currency does not match")
    try:
        expected = Decimal(str(expected_amount))
        received = Decimal(str(amount))
        valid = expected.is_finite() and received.is_finite() and expected > 0 and received == expected
    except (InvalidOperation, ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError("Payment amount does not match")


def money_to_minor_units(amount) -> int:
    """Exact two-decimal provider units; never truncate a binary float."""
    try:
        value = Decimal(str(amount))
        scaled = value * 100
        if not value.is_finite() or value <= 0 or scaled != scaled.to_integral_value():
            raise ValueError("Expected a positive two-decimal monetary amount")
        return int(scaled)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc

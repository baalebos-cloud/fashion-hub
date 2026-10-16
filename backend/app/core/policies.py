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

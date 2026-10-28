"""Platform analytics must never treat pending requests as paid volume."""
from decimal import Decimal

import pytest

from app.services.commerce_dashboard_service import summarize_payment_rows


def test_successful_payments_only_count_toward_reconciled_volume():
    result = summarize_payment_rows([
        ("paystack", "successful", 2, Decimal("1200.00")),
        ("interswitch", "pending", 4, Decimal("5000.00")),
        ("interswitch", "successful", 1, Decimal("700.50")),
        ("paystack", "failed", 5, Decimal("900.00")),
    ])
    assert result["verified_count"] == 3
    assert result["verified_volume_ngn"] == "1900.50"
    assert len(result["by_provider"]) == 4


def test_empty_ledger_does_not_fabricate_sales():
    result = summarize_payment_rows([])
    assert result["verified_count"] == 0
    assert result["verified_volume_ngn"] == "0.00"


def test_invalid_aggregate_is_rejected():
    with pytest.raises(ValueError):
        summarize_payment_rows([("interswitch", "successful", -1, Decimal("1"))])

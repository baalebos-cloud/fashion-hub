"""Read-only operational payment metrics based on persisted verified records.

No provider callbacks or browser claims are counted as completed payments.
Do not expose customer identities or estimate economic impact from this data.
"""
from decimal import Decimal
from sqlalchemy import func

from app.models.payment import Payment


def summarize_payment_rows(rows):
    results = []
    verified_volume = Decimal("0.00")
    verified_count = 0
    for provider, status, count, value in rows:
        count = int(count)
        volume = Decimal(str(value or 0))
        if not volume.is_finite() or count < 0:
            raise ValueError("Invalid aggregated payment data")
        results.append({
            "provider": provider, "status": status,
            "count": count, "amount_ngn": str(volume),
        })
        if status == "successful":
            verified_volume += volume
            verified_count += count
    return {
        "currency": "NGN",
        "verified_count": verified_count,
        "verified_volume_ngn": str(verified_volume),
        "by_provider": results,
        "note": "Only server-verified payment records count as successful.",
    }


def load_commerce_summary(db):
    rows = (db.query(
        Payment.provider, Payment.status,
        func.count(Payment.id), func.sum(Payment.amount),
    ).filter(Payment.currency == "NGN")
      .group_by(Payment.provider, Payment.status)
      .order_by(Payment.provider, Payment.status).all())
    return summarize_payment_rows(rows)

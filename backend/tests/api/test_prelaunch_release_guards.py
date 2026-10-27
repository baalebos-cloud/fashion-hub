"""Prelaunch financial safety and public verified-profile privacy."""
from unittest.mock import MagicMock
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.main import app
from app.models.professional import Professional
from app.services.payment_service import PaymentService


def test_live_payment_initialization_fails_closed_before_any_provider_call(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", False)
    service = PaymentService(MagicMock())
    service.provider = MagicMock()
    with pytest.raises(ConflictError, match="temporarily disabled"):
        service.initialize_payment_for_order(
            order_id=uuid.uuid4(), customer_email="buyer@example.com",
            callback_url="https://fashion-hub-tawny.vercel.app/payment/success",
            buyer_user_id=uuid.uuid4(),
        )
    service.provider.initialize_payment.assert_not_called()


def test_guessed_unverified_professional_id_is_not_public(db, make_user):
    seller = make_user(role="designer")
    profile = Professional(user_id=seller.id, professional_type="designer",
                           business_name="Unreviewed Shop", is_verified=False)
    db.add(profile)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            url = f"/api/v1/professionals/{profile.id}"
            assert client.get(url).status_code == 404
            profile.is_verified = True
            db.commit()
            assert client.get(url).status_code == 200
            seller.is_active = False
            db.commit()
            assert client.get(url).status_code == 404
    finally:
        app.dependency_overrides.clear()

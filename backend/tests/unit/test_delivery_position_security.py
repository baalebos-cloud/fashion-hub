"""Rider-position security contracts, without external location requests."""
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.exceptions import ForbiddenError
from app.schemas.delivery_position import RiderPositionInput
from app.services import delivery_position


@pytest.mark.parametrize("point", [
    {"latitude": float("nan"), "longitude": 5, "accuracy_m": 10, "share_token": "x" * 40},
    {"latitude": 7.6, "longitude": 181, "accuracy_m": 10, "share_token": "x" * 40},
    {"latitude": 7.6, "longitude": 5.2, "accuracy_m": 900, "share_token": "x" * 40},
])
def test_position_rejects_invalid_or_misleading_coordinates(point):
    with pytest.raises(ValidationError):
        RiderPositionInput.model_validate(point)


def test_revoked_token_cannot_publish_position(monkeypatch):
    fake = Mock()
    fake.eval.return_value = 0
    monkeypatch.setattr(delivery_position, "_client", lambda: fake)
    with pytest.raises(ForbiddenError):
        delivery_position.save_position(
            "delivery-1", share_token="revoked", latitude=7.64037,
            longitude=5.22102, accuracy_m=20,
        )
    assert fake.eval.call_count == 1


def test_publish_requires_atomic_consent_check(monkeypatch):
    fake = Mock()
    fake.eval.return_value = 1
    monkeypatch.setattr(delivery_position, "_client", lambda: fake)
    point = delivery_position.save_position(
        "delivery-1", share_token="valid-token", latitude=7.64037,
        longitude=5.22102, accuracy_m=20,
    )
    assert "share_token" not in point
    args = fake.eval.call_args.args
    assert "redis.call('GET'" in args[0]
    assert args[1] == 3  # consent, point, last fix: checked and written in one script
    assert args[-1] == delivery_position.MIN_INTERVAL_SECONDS

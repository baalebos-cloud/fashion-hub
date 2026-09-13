"""Unit tests for delivery request rejection/re-broadcast behavior."""
import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.services.delivery_request_service import DeliveryRequestService


def test_rejecting_a_delivery_request_resets_it_for_rebroadcast(db):
    service = DeliveryRequestService(db)
    # NOTE: broadcast_to_nearby_partners is unimplemented in this scaffold;
    # this test documents the expected contract for when it's wired in.
    with pytest.raises(NotImplementedError):
        service.broadcast_to_nearby_partners("00000000-0000-0000-0000-000000000000")

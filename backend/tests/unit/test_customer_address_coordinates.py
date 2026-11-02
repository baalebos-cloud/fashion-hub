"""Customer address payload requires precise delivery pin coordinates."""
import pytest
from pydantic import ValidationError
from app.schemas.address import CreateAddressRequest


def address(**overrides):
    return dict(
        label="Home", recipient_name="Test Customer", recipient_phone="08031234567",
        formatted_address="Ado-Iworoko Road, Ado Ekiti", city="Ado Ekiti",
        state_region="Ekiti", country="NG", **overrides,
    )


def test_requires_both_pin_coordinates():
    with pytest.raises(ValidationError):
        CreateAddressRequest.model_validate(address())
    with pytest.raises(ValidationError):
        CreateAddressRequest.model_validate(address(latitude=7.64037))


def test_valid_address_preserves_coordinates():
    payload = CreateAddressRequest.model_validate(address(latitude=7.64037, longitude=5.22104))
    assert payload.latitude == 7.64037
    assert payload.longitude == 5.22104


def test_rejects_invalid_coordinates_and_short_names():
    with pytest.raises(ValidationError):
        CreateAddressRequest.model_validate(address(latitude=95, longitude=5.22104))
    with pytest.raises(ValidationError):
        CreateAddressRequest.model_validate({**address(latitude=7.64037, longitude=5.22104), "recipient_name": "A"})

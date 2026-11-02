"""Shared location endpoint: Google first, configured secondary only on provider failure."""
from unittest.mock import patch, Mock
import pytest
from app.core.exceptions import ExternalProviderError
from app.integrations.maps.base import GeocodeResult
from app.integrations.maps.google_maps import GoogleMapsProvider
from app.api.v1.geocoding import reverse


def result():
    return GeocodeResult(7.64037, 5.22104, "Ado Road, Ekiti, Nigeria", "Ado Ekiti", "Ekiti", "Nigeria", None)


def test_google_success_does_not_call_secondary():
    provider = Mock()
    provider.reverse_geocode.return_value = result()
    with patch("app.api.v1.geocoding.get_map_provider", return_value=provider), \
         patch("app.api.v1.geocoding.reverse_geocode_fallback") as fallback:
        found = reverse(latitude=7.64037, longitude=5.22104, current_user=Mock())
        assert found.formatted_address == "Ado Road, Ekiti, Nigeria"
        fallback.assert_not_called()


def test_google_failure_uses_secondary():
    provider = Mock()
    provider.reverse_geocode.side_effect = ExternalProviderError("REQUEST_DENIED")
    with patch("app.api.v1.geocoding.get_map_provider", return_value=provider), \
         patch("app.api.v1.geocoding.settings") as config, \
         patch("app.api.v1.geocoding.reverse_geocode_fallback", return_value=result()) as fallback:
        config.GEOCODING_FALLBACK_URL = "https://nominatim.openstreetmap.org"
        found = reverse(latitude=7.64037, longitude=5.22104, current_user=Mock())
        assert found.city == "Ado Ekiti"
        fallback.assert_called_once_with(7.64037, 5.22104)


def test_google_rejects_http_200_error_status():
    response = Mock()
    response.json.return_value = {"status": "REQUEST_DENIED", "results": []}
    with patch("app.integrations.maps.google_maps.httpx.get", return_value=response):
        with pytest.raises(ExternalProviderError, match="REQUEST_DENIED"):
            GoogleMapsProvider(api_key="test").reverse_geocode(7.64037, 5.22104)

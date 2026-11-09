"""Reverse geocoding fills every part of a Nigerian address, from Google or OpenStreetMap."""
from unittest.mock import Mock, patch

from app.integrations.maps.google_maps import GoogleMapsProvider
from app.integrations.maps.nigeria_address import parse_google_reverse, parse_nominatim_reverse


def comp(name, *types):
    return {"long_name": name, "short_name": name, "types": list(types)}


# Shaped like a real Google answer for a point in Lekki: a plus code first, then the street address.
LEKKI = [
    {"types": ["plus_code"], "formatted_address": "CVXF+X4 Lekki, Lagos, Nigeria",
     "address_components": [comp("CVXF+X4", "plus_code"), comp("Lekki", "locality", "political")]},
    {"types": ["street_address"], "formatted_address": "14 Admiralty Way, Lekki Phase 1, Lekki 106104, Lagos, Nigeria",
     "address_components": [comp("14", "street_number"), comp("Admiralty Way", "route"),
                            comp("Lekki Phase 1", "neighborhood", "political"),
                            comp("Lekki", "locality", "political"),
                            comp("Eti-Osa", "administrative_area_level_2", "political"),
                            comp("Lagos", "administrative_area_level_1", "political"),
                            comp("Nigeria", "country", "political"), comp("106104", "postal_code")]},
]


def test_google_skips_the_plus_code_and_reads_every_part():
    found = parse_google_reverse(LEKKI, 6.4474, 3.4728)
    assert found.street == "14 Admiralty Way"
    assert found.area == "Lekki Phase 1"
    assert found.city == "Lekki"
    assert found.lga == "Eti-Osa"
    assert found.state_region == "Lagos"
    assert found.country == "Nigeria"
    assert found.postal_code == "106104"
    assert found.formatted_address.startswith("14 Admiralty Way")


def test_google_reads_types_beyond_the_first_and_fills_gaps_from_other_results():
    results = [
        {"types": ["route"], "formatted_address": "Herbert Macaulay Way, Yaba, Lagos, Nigeria",
         "address_components": [comp("Herbert Macaulay Way", "route"), comp("Yaba", "political", "sublocality", "sublocality_level_1"),
                                comp("Lagos", "administrative_area_level_1", "political")]},
        {"types": ["administrative_area_level_2", "political"], "formatted_address": "Lagos Mainland, Lagos, Nigeria",
         "address_components": [comp("Lagos Mainland", "administrative_area_level_2", "political"),
                                comp("Lagos", "locality", "political"), comp("Nigeria", "country", "political")]},
    ]
    found = parse_google_reverse(results, 6.5095, 3.3711)
    assert (found.street, found.area, found.city, found.lga, found.country) == (
        "Herbert Macaulay Way", "Yaba", "Lagos", "Lagos Mainland", "Nigeria")


def test_google_names_the_place_itself_as_the_landmark():
    results = [{"types": ["establishment", "point_of_interest"], "formatted_address": "Tejuosho Market, Yaba, Lagos",
                "address_components": [comp("Tejuosho Market", "establishment", "point_of_interest"),
                                       comp("Ojuelegba Road", "route"), comp("Yaba", "sublocality_level_1", "sublocality"),
                                       comp("Lagos", "locality"), comp("Lagos Mainland", "administrative_area_level_2")]}]
    found = parse_google_reverse(results, 6.507, 3.367)
    assert found.landmark == "Tejuosho Market"
    assert found.street == "Ojuelegba Road"


def test_nominatim_reads_the_lga_from_county():
    data = {"display_name": "Admiralty Way, Lekki Phase 1, Eti-Osa, Lagos State, 106104, Nigeria", "class": "highway",
            "name": "Admiralty Way",
            "address": {"house_number": "14", "road": "Admiralty Way", "suburb": "Lekki Phase 1", "city": "Lekki",
                        "county": "Eti-Osa", "state": "Lagos State", "postcode": "106104", "country": "Nigeria"}}
    found = parse_nominatim_reverse(data, 6.4474, 3.4728)
    assert (found.street, found.area, found.city, found.lga, found.state_region) == (
        "14 Admiralty Way", "Lekki Phase 1", "Lekki", "Eti-Osa", "Lagos State")
    assert found.landmark is None  # a road is not a landmark


def test_nominatim_landmark_from_a_named_place():
    data = {"display_name": "University of Ibadan, Ibadan North, Oyo State, Nigeria", "class": "amenity", "name": "University of Ibadan",
            "address": {"amenity": "University of Ibadan", "city": "Ibadan", "county": "Ibadan North", "state": "Oyo State", "country": "Nigeria"}}
    found = parse_nominatim_reverse(data, 7.44, 3.9)
    assert found.landmark == "University of Ibadan" and found.lga == "Ibadan North" and found.city == "Ibadan"


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_google_adds_the_nearest_bus_stop_and_a_landmark_when_places_is_available():
    def fake_get(url, params, timeout):
        if "geocode" in url:
            return _response({"status": "OK", "results": LEKKI})
        if params.get("type") == "bus_station":
            return _response({"status": "OK", "results": [{"name": "Jakande Bus Stop", "types": ["bus_station", "transit_station"],
                                                           "geometry": {"location": {"lat": 6.449, "lng": 3.474}}}]})
        return _response({"status": "OK", "results": [
            {"name": "Lekki", "types": ["locality", "political"], "geometry": {"location": {"lat": 6.44, "lng": 3.47}}},
            {"name": "Lekki Central Mosque", "types": ["mosque", "point_of_interest", "establishment"],
             "geometry": {"location": {"lat": 6.448, "lng": 3.473}}}]})
    with patch("app.integrations.maps.google_maps.httpx.get", side_effect=fake_get):
        found = GoogleMapsProvider(api_key="test").reverse_geocode(6.4474, 3.4728)
    assert found.nearest_bus_stop == "Jakande Bus Stop"
    assert found.landmark == "Lekki Central Mosque"
    assert found.lga == "Eti-Osa"


def test_places_not_enabled_never_breaks_the_address():
    def fake_get(url, params, timeout):
        if "geocode" in url:
            return _response({"status": "OK", "results": LEKKI})
        return _response({"status": "REQUEST_DENIED", "results": []})
    with patch("app.integrations.maps.google_maps.httpx.get", side_effect=fake_get):
        found = GoogleMapsProvider(api_key="test").reverse_geocode(6.4474, 3.4728)
    assert found.street == "14 Admiralty Way" and found.nearest_bus_stop is None and found.landmark is None


def test_a_far_away_bus_stop_is_not_offered():
    def fake_get(url, params, timeout):
        if "geocode" in url:
            return _response({"status": "OK", "results": LEKKI})
        return _response({"status": "OK", "results": [{"name": "Far Stop", "types": ["bus_station"],
                                                       "geometry": {"location": {"lat": 6.60, "lng": 3.35}}}]})
    with patch("app.integrations.maps.google_maps.httpx.get", side_effect=fake_get):
        assert GoogleMapsProvider(api_key="test").reverse_geocode(6.4474, 3.4728).nearest_bus_stop is None


def test_osm_road_codes_become_something_a_rider_can_use():
    # What the live site returned for a point near Ado-Ekiti.
    data = {"display_name": "F209, Adó-Èkìtì, Irepodun/Ifelodun, Ekiti, Nigeria", "class": "highway", "name": "F209",
            "address": {"road": "F209", "city": "Adó-Èkìtì", "county": "Irepodun/Ifelodun", "state": "Ekiti", "country": "Nigeria"}}
    found = parse_nominatim_reverse(data, 7.64044, 5.22106)
    assert found.street == "Along F209 road"
    assert (found.city, found.lga, found.state_region) == ("Adó-Èkìtì", "Irepodun/Ifelodun", "Ekiti")
    assert found.landmark is None


def test_google_failure_reason_is_logged_without_the_key():
    from app.api.v1.geocoding import reverse
    from app.core.exceptions import ExternalProviderError
    provider = Mock()
    provider.reverse_geocode.side_effect = ExternalProviderError(
        "Google reverse geocoding unavailable (REQUEST_DENIED): API keys with referer restrictions cannot be used with this API.")
    with patch("app.api.v1.geocoding.get_map_provider", return_value=provider), \
         patch("app.api.v1.geocoding.settings") as config, \
         patch("app.api.v1.geocoding.reverse_geocode_fallback", return_value=Mock()), \
         patch("app.api.v1.geocoding.logger") as log:
        config.GEOCODING_FALLBACK_URL = "https://nominatim.openstreetmap.org"
        reverse(latitude=7.64, longitude=5.22, current_user=Mock())
    logged = " ".join(str(a) for a in log.warning.call_args.args)
    assert "REQUEST_DENIED" in logged and "referer restrictions" in logged
    assert "7.64" not in logged


def test_google_error_message_is_kept_in_the_error():
    import pytest
    from app.core.exceptions import ExternalProviderError
    with patch("app.integrations.maps.google_maps.httpx.get", return_value=_response(
            {"status": "REQUEST_DENIED", "error_message": "This API project is not authorized to use this API.", "results": []})):
        with pytest.raises(ExternalProviderError, match="not authorized"):
            GoogleMapsProvider(api_key="secret-key").reverse_geocode(7.64, 5.22)

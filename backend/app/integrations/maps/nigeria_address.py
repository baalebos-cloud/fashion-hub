"""Turning a geocoder's answer into the parts of a Nigerian address: street, area, city/town, LGA,
state, a landmark and the nearest bus stop.

Google: the first result for a Nigerian point is often a "plus code" (e.g. "XQ5G+2J Lagos") with
almost no address parts, and a component's first type isn't always the useful one. So results are
ranked (street address first, plus codes last) and every component type is read, falling back to the
other results for anything the best one lacks. The LGA is Google's administrative_area_level_2.

OpenStreetMap / Nominatim: Nigerian LGAs are admin level 6, which Nominatim reports as "county".
"""
from app.integrations.maps.base import GeocodeResult

_GOOGLE_RANK = ("street_address", "premise", "subpremise", "establishment", "point_of_interest", "route",
                "neighborhood", "sublocality_level_2", "sublocality_level_1", "sublocality", "locality")


def _clean(value) -> str | None:
    text = " ".join(str(value or "").split())
    return text or None


def parse_google_reverse(results: list[dict], latitude: float, longitude: float) -> GeocodeResult:
    usable = [r for r in results if "plus_code" not in (r.get("types") or [])] or results
    best = next((r for kind in _GOOGLE_RANK for r in usable if kind in (r.get("types") or [])), usable[0])
    ordered = [best] + [r for r in usable if r is not best]

    def part(*kinds: str, only_best: bool = False) -> str | None:
        for result in ([best] if only_best else ordered):
            for component in result.get("address_components") or []:
                types = component.get("types") or []
                if any(kind in types for kind in kinds):
                    return _clean(component.get("long_name"))
        return None

    number, route = part("street_number", only_best=True), part("route")
    street = _clean(" ".join(p for p in (number, route) if p))
    area = part("neighborhood", "sublocality_level_2", "sublocality_level_1", "sublocality")
    city = part("locality", "postal_town") or area or part("administrative_area_level_2")
    if area and city and area.lower() == city.lower():
        area = None
    landmark = part("point_of_interest", "establishment", "premise", only_best=True)
    return GeocodeResult(
        latitude=latitude, longitude=longitude,
        formatted_address=best.get("formatted_address") or "",
        city=city, state_region=part("administrative_area_level_1"), country=part("country"),
        postal_code=part("postal_code"), street=street, area=area,
        lga=part("administrative_area_level_2"), landmark=landmark,
    )


_NOT_LANDMARKS = {"highway", "place", "boundary", "landuse", "natural"}


def parse_nominatim_reverse(data: dict, latitude: float, longitude: float) -> GeocodeResult:
    addr = data.get("address") or {}
    street = _clean(" ".join(p for p in (addr.get("house_number"), addr.get("road")) if p))
    area = _clean(addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or addr.get("city_district"))
    city = _clean(addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")) or area
    if area and city and area.lower() == city.lower():
        area = None
    name = _clean(data.get("name"))
    landmark = name if name and data.get("class") not in _NOT_LANDMARKS and name != addr.get("road") else None
    return GeocodeResult(
        latitude=latitude, longitude=longitude, formatted_address=data.get("display_name") or "",
        city=city, state_region=_clean(addr.get("state")), country=_clean(addr.get("country")),
        postal_code=_clean(addr.get("postcode")), street=street, area=area,
        lga=_clean(addr.get("county") or addr.get("state_district")), landmark=landmark,
    )

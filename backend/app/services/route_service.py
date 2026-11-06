"""Road routing behind one interface, with honest fallbacks.

    route(origin, destination, vehicle) -> RouteEstimate

Providers (ROUTING_PROVIDER):
  - "google": Google Routes API computeRoutes, traffic-aware. Needs ROUTING_GOOGLE_API_KEY and
    billing enabled on that Google Cloud project.
  - "osrm":   any OSRM server (ROUTING_OSRM_URL), e.g. one you host. Road distance and free-flow
    duration, no live traffic. The public demo server is for development only.
  - "none":   no provider; every answer is the labelled straight-line estimate.

Every answer says where it came from (`source`) and when (`computed_at`). If the provider is
off, slow, failing, rate-limited or finds no road route, the caller still gets an answer: the
straight-line estimate, marked `verified=False`. Nothing here blocks an order.

Resilience: per-request timeout, one bounded retry on transient errors, a circuit breaker
shared through Redis (opens after repeated failures or a 429), and a Redis cache keyed by
provider, vehicle and coordinates rounded to about 11 m.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import httpx
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger
from app.services.dispatch_pricing import URBAN_SPEED_KMH, road_km
from app.services.dispatch_routing import estimate_straight_line_km

logger = get_logger(__name__)

SOURCE_ESTIMATE = "straight_line_estimate"
TRANSIENT_STATUS = {500, 502, 503, 504}


@dataclass
class RouteEstimate:
    distance_km: float | None
    duration_minutes: int | None
    source: str                      # google_routes | osrm | straight_line_estimate
    verified: bool                   # True only for a real road route from a provider
    traffic_aware: bool = False
    polyline: str | None = None      # encoded polyline (Google/OSRM format) when available
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cached: bool = False
    fallback_reason: str | None = None

    def public(self, *, include_polyline: bool = False) -> dict:
        data = asdict(self)
        if not include_polyline:
            data.pop("polyline")
        return data


class RoutingUnavailable(Exception):
    """Provider can't answer right now (timeout, 5xx, rate limit, breaker open)."""


class NoRoute(Exception):
    """Provider answered: there is no road route between these points."""


# ---- fallback --------------------------------------------------------------------------------
def straight_line_estimate(origin: dict, destination: dict, vehicle: str | None, reason: str | None) -> RouteEstimate:
    km = estimate_straight_line_km(origin, destination)
    approx = road_km(km)
    speed = URBAN_SPEED_KMH.get(vehicle or "bike", URBAN_SPEED_KMH["bike"])
    minutes = max(1, round(approx / speed * 60)) if approx is not None else None
    return RouteEstimate(distance_km=approx, duration_minutes=minutes, source=SOURCE_ESTIMATE,
                         verified=False, fallback_reason=reason)


# ---- providers -------------------------------------------------------------------------------
def _google(origin: dict, destination: dict, vehicle: str | None) -> RouteEstimate:
    if not settings.ROUTING_GOOGLE_API_KEY:
        raise RoutingUnavailable("ROUTING_GOOGLE_API_KEY is not set")
    mode = "TWO_WHEELER" if vehicle == "bike" and settings.ROUTING_GOOGLE_TWO_WHEELER else (
        "WALK" if vehicle == "foot" else "DRIVE")
    body = {
        "origin": {"location": {"latLng": {"latitude": origin["latitude"], "longitude": origin["longitude"]}}},
        "destination": {"location": {"latLng": {"latitude": destination["latitude"], "longitude": destination["longitude"]}}},
        "travelMode": mode,
        **({"routingPreference": "TRAFFIC_AWARE"} if mode in {"DRIVE", "TWO_WHEELER"} else {}),
    }
    response = httpx.post(
        "https://routes.googleapis.com/directions/v2:computeRoutes", json=body,
        headers={"X-Goog-Api-Key": settings.ROUTING_GOOGLE_API_KEY,
                 "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline"},
        timeout=settings.ROUTING_TIMEOUT_SECONDS)
    _raise_for_status(response)
    routes = (response.json() or {}).get("routes") or []
    if not routes or "distanceMeters" not in routes[0]:
        raise NoRoute("no road route")
    first = routes[0]
    seconds = float(str(first.get("duration", "0s")).rstrip("s") or 0)
    return RouteEstimate(distance_km=round(first["distanceMeters"] / 1000, 1),
                         duration_minutes=max(1, round(seconds / 60)), source="google_routes", verified=True,
                         traffic_aware=mode in {"DRIVE", "TWO_WHEELER"},
                         polyline=(first.get("polyline") or {}).get("encodedPolyline"))


def _osrm(origin: dict, destination: dict, vehicle: str | None) -> RouteEstimate:
    if not settings.ROUTING_OSRM_URL:
        raise RoutingUnavailable("ROUTING_OSRM_URL is not set")
    profile = "foot" if vehicle == "foot" else "driving"
    coords = f"{origin['longitude']},{origin['latitude']};{destination['longitude']},{destination['latitude']}"
    response = httpx.get(f"{settings.ROUTING_OSRM_URL.rstrip('/')}/route/v1/{profile}/{coords}",
                         params={"overview": "simplified", "geometries": "polyline"},
                         timeout=settings.ROUTING_TIMEOUT_SECONDS)
    if response.status_code == 400 and (response.json() or {}).get("code") in {"NoRoute", "NoSegment"}:
        raise NoRoute("no road route")
    _raise_for_status(response)
    payload = response.json() or {}
    if payload.get("code") in {"NoRoute", "NoSegment"} or not payload.get("routes"):
        raise NoRoute("no road route")
    first = payload["routes"][0]
    return RouteEstimate(distance_km=round(first["distance"] / 1000, 1),
                         duration_minutes=max(1, round(first["duration"] / 60)), source="osrm", verified=True,
                         traffic_aware=False, polyline=first.get("geometry"))


PROVIDERS = {"google": _google, "osrm": _osrm}


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 429:
        retry_after = response.headers.get("retry-after", "")
        raise RoutingUnavailable(f"rate_limited:{retry_after if retry_after.isdigit() else ''}")
    if response.status_code in TRANSIENT_STATUS:
        raise RoutingUnavailable(f"http_{response.status_code}")
    if response.status_code >= 400:
        # 400/401/403: our request or our key is wrong. Not transient; trip the breaker.
        raise RoutingUnavailable(f"http_{response.status_code}")


# ---- shared state: cache, breaker, health ------------------------------------------------------
def _redis() -> Redis | None:
    try:
        return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        return None


def _key(*parts) -> str:
    return "routing:" + ":".join(str(p) for p in parts)


def _cache_key(provider: str, origin: dict, destination: dict, vehicle: str | None) -> str:
    def r(point):
        return f"{point['latitude']:.4f},{point['longitude']:.4f}"
    return _key("route", provider, vehicle or "bike", r(origin), r(destination))


def breaker_open(provider: str) -> bool:
    redis = _redis()
    try:
        return bool(redis and redis.exists(_key("breaker", provider)))
    except RedisError:
        return False


def _record_failure(provider: str, reason: str) -> None:
    redis = _redis()
    if not redis:
        return
    try:
        failures = redis.incr(_key("failures", provider))
        redis.expire(_key("failures", provider), settings.ROUTING_BREAKER_WINDOW_SECONDS)
        cooldown = settings.ROUTING_BREAKER_COOLDOWN_SECONDS
        if reason.startswith("rate_limited:") and reason.split(":", 1)[1].isdigit():
            cooldown = max(cooldown, min(int(reason.split(":", 1)[1]), 900))
        if failures >= settings.ROUTING_BREAKER_THRESHOLD or reason.startswith("rate_limited") \
                or reason in {"http_400", "http_401", "http_403"}:
            redis.set(_key("breaker", provider), reason, ex=cooldown)
        redis.hset(_key("health", provider), mapping={"last_failure_at": _now(), "last_failure": reason[:80]})
    except RedisError:
        pass


def _record_success(provider: str, latency_ms: int) -> None:
    redis = _redis()
    if not redis:
        return
    try:
        redis.delete(_key("failures", provider))
        redis.hset(_key("health", provider), mapping={"last_success_at": _now(), "last_latency_ms": latency_ms})
        redis.hincrby(_key("health", provider), "successes", 1)
    except RedisError:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def health() -> dict:
    """What the admin sees: which provider, is it answering, how fast, breaker state."""
    provider = settings.ROUTING_PROVIDER
    info = {"provider": provider, "configured": provider in PROVIDERS, "breaker_open": False}
    if provider not in PROVIDERS:
        info["note"] = "No routing provider configured; distances and ETAs are straight-line estimates."
        return info
    redis = _redis()
    try:
        raw = redis.hgetall(_key("health", provider)) if redis else {}
        info.update({k.decode(): v.decode() for k, v in raw.items()})
        info["breaker_open"] = bool(redis and redis.exists(_key("breaker", provider)))
    except RedisError:
        info["note"] = "Routing health unavailable (Redis)."
    return info


# ---- entry point -------------------------------------------------------------------------------
def route(origin: dict | None, destination: dict | None, vehicle: str | None = "bike", *,
          cache_seconds: int | None = None, bypass_cache: bool = False) -> RouteEstimate | None:
    """Road route when a provider can give one, otherwise the labelled straight-line estimate.
    Returns None only when a point is missing."""
    if origin is None or destination is None:
        return None
    provider = settings.ROUTING_PROVIDER
    fetch = PROVIDERS.get(provider)
    if fetch is None:
        return straight_line_estimate(origin, destination, vehicle, "no_provider")
    if breaker_open(provider):
        return straight_line_estimate(origin, destination, vehicle, "provider_paused")

    redis = _redis()
    key = _cache_key(provider, origin, destination, vehicle)
    try:
        hit = redis.get(key) if redis and not bypass_cache else None
        if hit:
            cached = RouteEstimate(**json.loads(hit))
            cached.cached = True
            return cached
    except (RedisError, ValueError, TypeError):
        pass

    last_reason = "unavailable"
    for attempt in range(1 + max(0, settings.ROUTING_RETRIES)):
        started = time.monotonic()
        try:
            result = fetch(origin, destination, vehicle)
        except NoRoute:
            return straight_line_estimate(origin, destination, vehicle, "no_road_route")
        except (RoutingUnavailable, httpx.TimeoutException, httpx.TransportError, ValueError, KeyError) as exc:
            last_reason = str(exc) if isinstance(exc, RoutingUnavailable) else type(exc).__name__.lower()
            if last_reason.startswith("rate_limited") or last_reason in {"http_400", "http_401", "http_403"}:
                break  # retrying won't help
            if attempt < settings.ROUTING_RETRIES:
                time.sleep(min(0.25 * (2 ** attempt), 1.0))
            continue
        _record_success(provider, round((time.monotonic() - started) * 1000))
        ttl = cache_seconds if cache_seconds is not None else (
            settings.ROUTING_TRAFFIC_CACHE_SECONDS if result.traffic_aware else settings.ROUTING_CACHE_SECONDS)
        try:
            if redis and ttl > 0:
                redis.set(key, json.dumps(asdict(result)), ex=ttl)
        except RedisError:
            pass
        return result
    _record_failure(provider, last_reason)
    logger.warning("routing_fallback", extra={"provider": provider, "reason": last_reason[:80]})
    return straight_line_estimate(origin, destination, vehicle, "provider_unavailable")


def live_route(delivery_id, origin: dict | None, destination: dict | None, vehicle: str | None) -> RouteEstimate | None:
    """Rider-to-drop-off route for live ETAs, recomputed at most once per ROUTING_LIVE_ETA_SECONDS
    per delivery, however many people are watching.

    - A fresh live result is reused by everyone until it expires.
    - Only one request per delivery refreshes it (a short Redis lock); the others reuse the last
      live answer, or the labelled estimate if there's none yet, instead of calling the provider.
    - A refresh never reads the ordinary route cache, whose traffic data can be up to 15 min old.
    """
    if origin is None or destination is None:
        return None
    redis = _redis()
    key, last_key, lock_key = _key("live", delivery_id), _key("live-last", delivery_id), _key("live-lock", delivery_id)

    def load(k):
        raw = redis.get(k) if redis else None
        if not raw:
            return None
        cached = RouteEstimate(**json.loads(raw))
        cached.cached = True
        return cached

    try:
        fresh = load(key)
        if fresh is not None:
            return fresh
        lock_ttl = max(5, int(settings.ROUTING_TIMEOUT_SECONDS * (settings.ROUTING_RETRIES + 1)) + 2)
        if redis is not None and not redis.set(lock_key, "1", nx=True, ex=lock_ttl):
            # Someone else is refreshing this delivery right now.
            return load(last_key) or straight_line_estimate(origin, destination, vehicle, "refresh_in_progress")
    except (RedisError, ValueError, TypeError):
        redis = None  # no shared state: fall through and compute once for this request
    try:
        result = route(origin, destination, vehicle, cache_seconds=0, bypass_cache=True)
        if redis is not None and result is not None:
            payload = json.dumps(asdict(result))
            redis.set(key, payload, ex=max(5, settings.ROUTING_LIVE_ETA_SECONDS))
            redis.set(last_key, payload, ex=max(60, settings.ROUTING_LIVE_ETA_SECONDS * 10))
        return result
    except RedisError:
        return result
    finally:
        try:
            if redis is not None:
                redis.delete(lock_key)
        except RedisError:
            pass


def stored_route(request) -> dict | None:
    """The route saved on a delivery request, in the same shape as RouteEstimate.public()."""
    if request is None or request.route_source is None:
        return None
    return {"distance_km": float(request.route_distance_km) if request.route_distance_km is not None else None,
            "duration_minutes": request.route_duration_minutes, "source": request.route_source,
            "verified": request.route_source != SOURCE_ESTIMATE,
            "traffic_aware": request.route_source == "google_routes",
            "computed_at": request.route_computed_at.isoformat() if request.route_computed_at else None,
            "cached": True, "fallback_reason": None}


# ---- travel-time matrix (multi-stop planning) ------------------------------------------------
def _estimate_matrix(points: list[dict], vehicle: str | None) -> list[list[int]]:
    return [[0 if i == j else (straight_line_estimate(a, b, vehicle, None).duration_minutes or 1)
             for j, b in enumerate(points)] for i, a in enumerate(points)]


def _google_matrix(points: list[dict], vehicle: str | None) -> list[list[int]]:
    if not settings.ROUTING_GOOGLE_API_KEY:
        raise RoutingUnavailable("ROUTING_GOOGLE_API_KEY is not set")
    waypoints = [{"waypoint": {"location": {"latLng": {"latitude": p["latitude"], "longitude": p["longitude"]}}}}
                 for p in points]
    body = {"origins": waypoints, "destinations": waypoints, "travelMode": "DRIVE"}
    if len(points) ** 2 <= 100:  # Google allows at most 100 elements with live traffic
        body["routingPreference"] = "TRAFFIC_AWARE"
    response = httpx.post("https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix", json=body,
                          headers={"X-Goog-Api-Key": settings.ROUTING_GOOGLE_API_KEY,
                                   "X-Goog-FieldMask": "originIndex,destinationIndex,duration,condition"},
                          timeout=settings.ROUTING_TIMEOUT_SECONDS * 2)
    _raise_for_status(response)
    fallback = _estimate_matrix(points, vehicle)
    matrix = [row[:] for row in fallback]
    for element in response.json() or []:
        i, j = element.get("originIndex", 0), element.get("destinationIndex", 0)
        if element.get("condition") == "ROUTE_EXISTS" and "duration" in element:
            matrix[i][j] = 0 if i == j else max(1, round(float(str(element["duration"]).rstrip("s")) / 60))
    return matrix


def _osrm_matrix(points: list[dict], vehicle: str | None) -> list[list[int]]:
    if not settings.ROUTING_OSRM_URL:
        raise RoutingUnavailable("ROUTING_OSRM_URL is not set")
    coords = ";".join(f"{p['longitude']},{p['latitude']}" for p in points)
    profile = "foot" if vehicle == "foot" else "driving"
    response = httpx.get(f"{settings.ROUTING_OSRM_URL.rstrip('/')}/table/v1/{profile}/{coords}",
                         params={"annotations": "duration"}, timeout=settings.ROUTING_TIMEOUT_SECONDS * 2)
    _raise_for_status(response)
    durations = (response.json() or {}).get("durations")
    if not durations:
        raise RoutingUnavailable("osrm_table_empty")
    fallback = _estimate_matrix(points, vehicle)
    return [[0 if i == j else (max(1, round(cell / 60)) if cell is not None else fallback[i][j])
             for j, cell in enumerate(row)] for i, row in enumerate(durations)]


MATRIX_PROVIDERS = {"google": _google_matrix, "osrm": _osrm_matrix}


def travel_matrix(points: list[dict], vehicle: str | None = "bike") -> tuple[list[list[int]], str]:
    """Minutes between every pair of points, and where they came from. Falls back to the labelled
    straight-line estimate (source "straight_line_estimate") exactly like route()."""
    provider = settings.ROUTING_PROVIDER
    fetch = MATRIX_PROVIDERS.get(provider)
    if fetch is None or len(points) < 2 or breaker_open(provider):
        return _estimate_matrix(points, vehicle), SOURCE_ESTIMATE
    redis = _redis()
    key = _key("matrix", provider, vehicle or "bike", "|".join(f"{p['latitude']:.4f},{p['longitude']:.4f}" for p in points))
    try:
        hit = redis.get(key) if redis else None
        if hit:
            return json.loads(hit), "google_routes" if provider == "google" else "osrm"
    except (RedisError, ValueError):
        pass
    started = time.monotonic()
    try:
        matrix = fetch(points, vehicle)
    except (RoutingUnavailable, httpx.TimeoutException, httpx.TransportError, ValueError, KeyError) as exc:
        _record_failure(provider, str(exc) if isinstance(exc, RoutingUnavailable) else type(exc).__name__.lower())
        return _estimate_matrix(points, vehicle), SOURCE_ESTIMATE
    _record_success(provider, round((time.monotonic() - started) * 1000))
    try:
        if redis:
            redis.set(key, json.dumps(matrix), ex=settings.ROUTING_TRAFFIC_CACHE_SECONDS if provider == "google"
                      else settings.ROUTING_CACHE_SECONDS)
    except RedisError:
        pass
    return matrix, "google_routes" if provider == "google" else "osrm"

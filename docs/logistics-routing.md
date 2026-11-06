# Road routing and ETAs (logistics phase 1)

## What changed

Distances and travel times used to be **straight-line distance × 1.35** everywhere. They now
come from a routing service (`backend/app/services/route_service.py`) with replaceable providers:

| `ROUTING_PROVIDER` | What you get | Needs |
|---|---|---|
| `none` (default) | The old straight-line estimate, labelled `straight_line_estimate`, `verified: false` | Nothing |
| `google` | Google Routes API road distance, **traffic-aware** duration, route line | `ROUTING_GOOGLE_API_KEY` (a *server* key with the Routes API enabled) and **billing on** |
| `osrm` | Road distance and free-flow duration (no live traffic), route line | `ROUTING_OSRM_URL` pointing at an OSRM server |

Every answer carries `source`, `verified`, `traffic_aware`, `computed_at` and, for estimates,
`fallback_reason` (`no_provider`, `provider_unavailable`, `provider_paused`, `no_road_route`).
The app never shows a straight-line estimate as a road route.

## Where routes are used

- **When a rider is requested:** the pickup → drop-off route is computed **once** and saved on the
  delivery request (migration `0027`). The job board, reserved-job card and seller dispatch panel
  read the saved route, so listing jobs never calls the provider.
- **Riders before claiming:** they see distance and time only. The route line (which traces exact
  addresses) goes **only to the assigned rider**, on the trip page.
- **Live ETA on the order journey and public tracking link:** rider position → drop-off,
  recomputed **at most once per minute per delivery** (`ROUTING_LIVE_ETA_SECONDS`), however many
  people are watching. It's labelled "Road route" or "Estimate".
- **Admin → Deliveries:** a line showing which provider is in use, its last response time, and
  whether it's paused. Also `GET /api/v1/admin/routing/health`.
- **Unchanged on purpose:** proximity alerts and auto-offer ranking still use straight-line distance.
  Auto-offer ranking moves to road-time matrices in phase 3.

## Fares: unchanged until you approve

Suggested fares still use the existing formula. Switching `DISPATCH_PRICE_FROM_ROAD_ROUTES=true`
prices new requests from the **verified road distance** with the same base and per-km rates. That
usually means somewhat higher fares for winding routes. A fee already on the order is always kept.

## Failure handling

- **Timeouts and retries:** 3-second timeout (`ROUTING_TIMEOUT_SECONDS`), then one retry after 250 ms on timeouts and 5xx.
- **Circuit breaker:** shared across API workers through Redis. It pauses the provider for
  `ROUTING_BREAKER_COOLDOWN_SECONDS` after `ROUTING_BREAKER_THRESHOLD` failures within
  `ROUTING_BREAKER_WINDOW_SECONDS`. It pauses immediately on a 429 (respecting `Retry-After`, up
  to 15 minutes) or a 400/401/403 (a bad key or bad request).
- **Caching:** traffic-aware routes are cached 15 minutes (`ROUTING_TRAFFIC_CACHE_SECONDS`), others 24 hours
  (`ROUTING_CACHE_SECONDS`). The cache key rounds coordinates to about 11 m.
- **Nothing is blocked:** if routing fails, the request is still created with the labelled estimate.
- **No location data in logs:** fallbacks log only the provider and reason, never coordinates.

## Choosing a provider

| Option | Coverage in Lagos/Abuja | Traffic | Cost | Notes |
|---|---|---|---|---|
| **Google Routes API** | Best available | Yes | Pay per request; check Google's current Routes pricing. Traffic-aware requests cost more than basic | Same vendor as the site's maps; needs billing (currently off) |
| OSRM (self-hosted, OpenStreetMap) | Good on main roads; thinner on small streets | No | Server cost only (small VPS; Nigeria extract) | Adapter included |
| Valhalla (self-hosted) | Same OSM data | No | Server cost only | Has a motorcycle profile; adapter not built yet |
| GraphHopper (hosted) | OSM data | Limited | Free tier, then paid | Not built |

**Recommendation:** use **Google Routes** as the primary provider once billing is enabled. It has the best
coverage and live traffic, which matters most for Lagos ETAs. Keep `osrm` as the no-cost alternative
if you later self-host it. Don't point production at the public OSRM demo server: its usage policy
doesn't allow that.

## Turning it on (owner)

1. In Google Cloud (the project with billing), enable the **Routes API**. Create a **server** API
   key restricted to the Routes API. Don't reuse the browser maps key.
2. On Railway (API service): `ROUTING_PROVIDER=google`, `ROUTING_GOOGLE_API_KEY=<key>`.
3. Check Admin → Deliveries: the routing line should name Google Routes with a response time.
4. Later, once you've reviewed the price impact: `DISPATCH_PRICE_FROM_ROAD_ROUTES=true`.

## Rollback

- **Instant:** set `ROUTING_PROVIDER=none`. Everything goes back to labelled estimates; no deploy needed.
- **Code:** revert the PR. Migration `0027` only adds nullable columns to `delivery_requests`. Downgrade
  with `alembic downgrade 0026`; the saved routes are dropped and nothing else changes.

## Tests (all with faked providers; no real API calls)

`backend/tests/api/test_road_routing.py`:
- **Provider answers:** a Google route parsed, cached and labelled; OSRM routes; no road route; a missing key.
- **Failures:** a timeout retries then falls back; repeated failures open the breaker; a 429 pauses without retrying; a bad key pauses the provider.
- **Live ETAs:** throttled to one provider call per minute per delivery.
- **End to end:** the route is stored on request; the job board shows no route line and makes no provider calls; the assigned rider gets the line; dispatch works with the provider down; fares are unchanged until the flag is on; admin health works.

# Maps & GPS

## Provider abstraction

```
MapProvider (ABC)          app/integrations/maps/base.py
├── GoogleMapsProvider     app/integrations/maps/google_maps.py
└── MapboxProvider         app/integrations/maps/mapbox.py
```

`get_map_provider()` resolves the active provider from
`settings.MAP_PROVIDER`. Supports geocode, reverse geocode, and
distance/duration calculation.

## PostGIS

`locations.geom` is a `geography(Point, 4326)` column (via GeoAlchemy2).
Nearby-search queries use `ST_DWithin`:

```sql
SELECT p.* FROM professionals p
JOIN locations l ON p.location_id = l.id
WHERE ST_DWithin(l.geom, ST_MakePoint(:lng, :lat)::geography, :radius_m)
ORDER BY l.geom <-> ST_MakePoint(:lng, :lat)::geography
LIMIT :limit;
```

See `DistanceService.find_nearby_professionals` (stubbed with this exact
query documented in its docstring) and
`DeliveryRequestService.broadcast_to_nearby_partners` for the delivery-side
equivalent.

## Geocoding cache

`GeocodingService` caches geocode results in Redis for 24h keyed by the
normalized address string, since addresses rarely change and this
meaningfully reduces provider API cost/latency.

## Privacy: precision truncation

`LocationService.to_public_view` rounds coordinates to ~2 decimal places
(~1.1km) for public listing contexts (e.g. "tailors near you" before an
order exists). Full precision is only exposed to users who need it for
actual fulfillment — the assigned delivery partner and the two parties to
an order.

## Delivery fee calculation

`DistanceService.calculate_delivery_fee(base_fee, per_km_rate, ...)` —
uses the configured `MapProvider`'s driving distance, not straight-line
distance, for a realistic fee estimate.

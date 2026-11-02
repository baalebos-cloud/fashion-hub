# Reverse-geocoding operations

The authenticated `GET /api/v1/geocoding/reverse` endpoint is shared by the map picker and any customer, professional, vendor or courier workflow calling the existing frontend `reverseGeocode` helper. Google/Mapbox remains the configured primary. Secondary fallback runs only when the primary provider raises an ExternalProviderError.

* `MAPS_API_KEY`: server-side Google Maps Geocoding API key; enable the **Geocoding API**, billing and compatible server/IP restrictions. The Vercel `VITE_MAPS_PUBLIC_KEY` is separate and only loads the browser map.
* `GEOCODING_FALLBACK_URL`: opt-in HTTPS base URL for a Nominatim-compatible reverse-geocoding provider, e.g. `https://nominatim.openstreetmap.org` for **low-volume testing only**.
* `GEOCODING_CONTACT_EMAIL`: valid project contact address for provider identification.
* `REDIS_URL`: shared Redis instance for a seven-day result cache and a distributed two-second throttle. If Redis is unavailable, the secondary service is not called, ensuring rate-limit protection.

Public Nominatim is **not** a guaranteed production SLA. Its [usage policy](https://operations.osmfoundation.org/policies/nominatim/) requires an identifying User-Agent, attribution, caching and a strict aggregate maximum of one request per second. Fashion Hub intentionally limits to one fallback request every two seconds; if the quota is exhausted, users can save verified coordinates with an editable manually entered street address. For high-traffic production use, configure a properly licensed hosted Nominatim provider or a privately operated instance. Display appropriate OpenStreetMap contributor attribution if OSM results are surfaced in the product.

Do not infer a road name from coordinates if every provider fails; users must confirm the manual address. Never use route or distance geocoding requests for systematic bulk reverse lookup. No payment or role-based authorization policies are altered.

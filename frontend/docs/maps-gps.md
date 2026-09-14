# Maps & GPS

Client-side, this app only ever does **display** (rendering a map,
showing a pin, letting someone drag a marker) and **browser geolocation**
(`lib/maps/geolocation.ts`). Geocoding, reverse geocoding, and distance
calculations always go through the backend
(`lib/maps/geocoding.ts` -> `POST/GET /geocoding/*`) — see
`backend/docs/maps-and-gps.md`. This keeps the server-side maps API key
(and its Redis caching layer) entirely out of the browser.

`config/map.config.ts` only ever holds a public/restricted map-display
key, never a key capable of billed geocoding calls.

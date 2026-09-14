# Tracking

`hooks/use-tracking.ts` polls `GET /orders/{id}/tracking` every 15s while
an order is in an active delivery state. This is a deliberate zero-infra
default — swap the interval-based poll for a WebSocket subscription once
the backend exposes one, without changing any component that consumes
`useTracking`.

`components/tracking/TrackingMap.tsx` is a placeholder render surface;
wire in real marker rendering via `hooks/use-map.ts` once the map SDK
script is confirmed loaded (see `lib/maps/map-client.ts`).

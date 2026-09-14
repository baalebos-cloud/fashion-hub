# Delivery Partner Flow

`pages/delivery/DeliveryRequests.tsx` shows broadcasted requests (see
`backend/docs/delivery.md`); accepting one creates an active delivery
(`ActiveDeliveries.tsx` -> `DeliveryDetails.tsx`). `Pickup.tsx` and
`Dropoff.tsx` wrap the corresponding confirmation actions, with
`components/tracking/ProofOfDelivery.tsx` capturing photo evidence at
drop-off. `Navigation.tsx` renders `components/delivery/DeliveryMap.tsx`
for the active route.

GPS pings are expected to be sent periodically while a delivery is active
— the backend's staleness job
(`backend/app/workers/tracking_tasks.py::check_stale_tracking_task`) flags
a delivery whose `last_ping_at` goes quiet for too long, so this flow
should ensure `hooks/use-tracking.ts`-equivalent ping submission runs
reliably in the delivery partner's app, not just the read-side polling
used elsewhere.

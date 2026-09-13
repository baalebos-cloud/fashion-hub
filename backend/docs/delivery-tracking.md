# Delivery Tracking

## Data model

- `DeliveryTracking` — the current, frequently-overwritten snapshot
  (latest lat/lng, status, ETA, `last_ping_at`).
- `TrackingEvent` — append-only log of every ping/status change, used for
  route replay and dispute investigation.

## Recording a ping

`TrackingService.record_gps_ping` (called from the delivery partner app)
updates `DeliveryTracking` and appends a `TrackingEvent`.

## Edge case: GPS temporarily stops updating

`app/workers/tracking_tasks.py::check_stale_tracking_task` runs every 2
minutes (Celery beat) and flags any delivery that is
`picked_up`/`in_transit`/`out_for_delivery` but whose `last_ping_at` is
older than `STALE_THRESHOLD_MINUTES` (default 15). It triggers
`notify_delivery_tracking_stale_task`, which notifies the delivery partner
(and, in a full implementation, support/the customer) — the system never
silently lets a delivery go dark.

## Customer-facing endpoint

`GET /api/v1/orders/{order_id}/tracking` — thin route delegating to
`TrackingService.get_tracking_for_order`; access-controlled to the order's
buyer/seller (and admins) via the same pattern as other order sub-resources.

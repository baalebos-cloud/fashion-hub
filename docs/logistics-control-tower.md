# Dispatcher control tower (logistics phase 5)

The control tower is the top of **Admin → Deliveries**. It extends the existing page and doesn't
replace it. It refreshes every 30 seconds and has three tabs.

## Needs attention

These deterministic rules run each time the page loads (`app/services/control_tower_service.py`).
They're sorted critical first, then by how long the problem has lasted. Each one says what happened
and what to do next.

| Alert | Fires when | Critical when |
|---|---|---|
| No rider yet | a job has waited more than `DISPATCH_ALERT_UNASSIGNED_MIN` (15) | twice that |
| Late pickup | assigned but not collected after `DISPATCH_ALERT_PICKUP_MIN` (30) | twice that |
| Late delivery | on the road longer than route time × `DISPATCH_ALERT_DROPOFF_FACTOR` (1.5) + `DISPATCH_ALERT_DROPOFF_GRACE_MIN` (15), or `DISPATCH_ALERT_DROPOFF_MIN` (90) with no route time | twice that |
| Tracking lost | travelling for `DISPATCH_ALERT_TRACKING_MIN` (5)+ min with no live or recent location | — |
| Location off | the rider's phone reported permission denied | — |
| Off route | the rider is more than `DISPATCH_ALERT_OFF_ROUTE_KM` (3 km) further from the drop-off than the whole trip is long | — |
| Rider issue | an open rider issue report | when status is OPEN |

The rules never change a delivery. The dispatcher acts with the existing tools: release, reassign,
suggested riders and assign, and issue triage. These are all audited and keep the existing rule
that no reassignment happens after collection.

## Riders

Every verified rider is shown as **online and free**, **offline**, or **on N deliveries**, with location freshness
(live, delayed, last seen, location off). No coordinates are shown.

## Today

From midnight UTC:
- jobs requested and delivered
- median time to find a rider, median time to pickup, median trip time
- the share of automatic offers accepted

Medians are used so that one very slow delivery doesn't distort the picture.

## API (admin only)

- `GET /api/v1/admin/dispatch/control-tower` returns `{exceptions, performance, generated_at}`.
- `GET /api/v1/admin/dispatch/riders/overview` returns the riders list.

## Not included

- **A live map of all riders:** the site's maps use Google Maps, whose billing is off on the live domain.
  Once billing is enabled, a fleet map can plot the same riders and positions, admin-only.
  Positions are already available to admins per delivery.
- **Push alerts** (SMS, WhatsApp, sound): the alerts are on the page only. A Celery task could send critical
  ones later.

## Rollback

There are no migrations or flags. Revert the PR. The thresholds are settings, so they can be tuned without a deploy.

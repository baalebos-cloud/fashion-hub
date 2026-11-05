# Fashion Hub internal dispatch: rider upgrade

This implementation is **Fashion Hub-native** (FastAPI, PostgreSQL/PostGIS,
Redis, React/Vite). Sage reference patterns were inspected for validated
coordinates, explicit straight-line vs road routing, and capacity-aware
planning; **no Sage codebase, NestJS service, Prisma schema, or worker** is
installed in Fashion Hub.

## Actual supported lifecycle

1. The customer selects a delivery address before placing an order. Checkout
   preserves an order-specific address snapshot.
2. The tailor/designer marks an eligible customer order ready for delivery and
   creates `POST /api/v1/delivery-requests/orders/{order_id}`. This freezes
   shop pickup and customer drop-off into dedicated location snapshots. Only
   the current order seller may request dispatch.
3. Verified, available delivery partners see **summary-only** requests at
   `GET /api/v1/delivery-requests/available`. Neither personal contacts nor
   precise customer coordinates are exposed before assignment.
4. A rider atomically claims an available request using
   `POST /api/v1/delivery-requests/{id}/accept`. Database locks enforce
   exclusive assignment and partner availability.
5. The assigned rider opens `GET /api/v1/deliveries/{id}/trip` to view
   pickup/drop-off locations and contacts. Google Maps navigation, phone
   and WhatsApp links use only authorized details. Missing GPS shows a
   fallback; no fabricated distance or ETA is provided.
6. After collecting the package, the rider calls
   `POST /api/v1/deliveries/{id}/picked-up`; a ready order transitions to
   `out_for_delivery` and delivery to `in_transit`.
7. The customer views their order's assigned-rider status, contact card,
   and a **six-digit customer-only handover code** on their order page.
8. After handing over the package, the rider submits the customer-provided
   code to `POST /api/v1/deliveries/{id}/delivered`. The server enforces
   active assignment, order status and OTP verification with a Redis-backed
   shared attempt limit. No successful handover is simulated.
9. Customer and seller see role-authorized status and order timeline updates.
   The admin Dispatch page shows current queued requests, active assignments
   and verified available rider counts.

## GPS sharing (explicit opt-in only)

- The **assigned rider** presses **Start sharing my location** on the active
  navigation screen. The server returns a temporary consent token from
  `POST /api/v1/deliveries/{id}/position/start`.
- The client uses `navigator.geolocation.watchPosition` and sends at most
  one update about every 15 seconds to `POST /api/v1/deliveries/{id}/position`.
  The server validates latitude, longitude and <=200m reported accuracy.
- Redis atomically validates the session token for **each** upload, then
  stores the point with a **90-second TTL**. The consent itself expires in
  60 minutes. Customer, seller, assigned rider and admin may fetch the
  latest point at `GET /api/v1/deliveries/{id}/position` **only** while the
  delivery is `in_transit`.
- Stop or leaving the navigation screen revokes the consent and clears the
  point via `DELETE /api/v1/deliveries/{id}/position`. Concurrent late
  uploads cannot recreate a revoked point due to the atomic Redis script.
  If the connection fails, the point still expires automatically.
- This is **foreground browser GPS polling**, not a background-capable
  mobile tracking SDK, guaranteed continuous location, or a true traffic ETA.
  Devices denying geolocation retain the pickup/drop-off navigation links.

## Validation and rollout gates

Use **synthetic accounts and staging resources only**. Keep real payments
and refunds disabled. Suggested tests:

- Order buyer/seller roles, delivery partner A and B, and admin.
- Verify only seller can request pickup; two couriers cannot accept one job.
- Verify no customer contact or coordinates in unassigned request listings.
- Confirm assigned-rider pickup works directly from `ready_for_delivery`,
  with duplicate pickup rejected.
- Confirm courier B cannot read or post courier A's GPS, and buyer can
  only read GPS for their own active delivery.
- Start, publish, stop, then attempt to replay a previously issued GPS
  consent token. Replay must fail.
- Verify customer-only code access, wrong-code rejection, attempt limiting,
  and successful delivery only after correct code.
- Verify admin dispatch board counts and role restrictions.
- Verify notification/timeline, mobile navigation and recipient contact links.
- Run backend test suite, frontend lint/test/build, container checks,
  dependency-security audit, and a Vercel preview build **on the same head
  commit**. Do not merge if any check is red.

## Not yet delivered

Automatic GPS/vehicle-capacity matching, vendor-material dispatch,
traffic-aware or route-optimized ETA, automatic delivery fee/payout
recalculation, turn-by-turn navigation inside Fashion Hub, continuous
background GPS, and photo/signature proof. Straight-line haversine is
**not** a road distance or price estimate.

Only the Fashion Hub service/project and its PR branch are in scope.
Do not invoke live settlement or modify the Sage reference repository.

## Fares, rider offers and the delivery journey

**Suggested fare.** When a seller requests a courier, the request gets a
suggested fare unless the order already carries a delivery fee:
`DISPATCH_BASE_FARE + DISPATCH_PER_KM_FARE × road km`, where road km is the
straight-line pickup→drop-off distance × `DISPATCH_ROAD_FACTOR` (1.35),
rounded to the nearest ₦50 with a `DISPATCH_MIN_FARE` floor. Missing pins
fall back to the minimum fare.

**Job board.** `GET /delivery-requests/available` now returns priced job
cards: suggested fare, allowed offer range, approximate road km, and pickup
and drop-off **areas** (city/state). Exact addresses, coordinates and contacts
are still only available after assignment.

**Two ways to take a job.**
1. *Accept at the suggested fare* (`POST /delivery-requests/{id}/accept`),
   an instant atomic claim as before. The delivery fee is the suggested fare.
2. *Offer your own fare* (`POST /delivery-requests/{id}/offers`): an amount
   within 80–200% of the suggested fare plus minutes to pickup. One live offer
   per rider per job; offers expire after `DISPATCH_OFFER_TTL_MINUTES` (10).
   Riders can withdraw (`DELETE .../offers/mine`).

The order's seller sees live offers, cheapest first, each with a rider card
(first name, verified, rating, vehicle, completed deliveries) at
`GET /delivery-requests/orders/{order_id}/dispatch`, and accepts one with
`POST /delivery-requests/offers/{offer_id}/accept`. Acceptance re-checks under
row locks that the job is still open, the offer is unexpired and the rider is
still verified and available, then uses the same assignment path as instant
claims; all other pending offers are declined.

**Delivery journey.** `GET /deliveries/orders/{order_id}/journey` (buyer,
seller, assigned rider, admin) returns a tracking number and ordered
milestones (placed, paid, accepted, in production, ready, looking for a rider,
rider assigned, picked up, delivered, received) with timestamps and
`done/current/upcoming` states. While the rider shares GPS and the delivery
is in transit, it adds an approximate ETA and remaining distance labelled
`live_gps_estimate`. It is straight-line × road factor at typical city
speeds, not traffic-aware routing.

# Logistics audit and phased plan (2026-11-05)

Audit of Fashion Hub (Tailora) delivery code against the logistics mission brief.
Status reflects `main` after PRs #116–#129. "Verified" means covered by automated
tests in CI; nothing below has been certified end-to-end in staging with real riders.

## Capability and gap matrix

| # | Capability | Status | Evidence |
|---|---|---|---|
| 1 | Tailor → customer dispatch request, immutable pickup/drop-off snapshots | Implemented, test-verified | `services/internal_courier_service.py::request`, `tests/api/test_internal_courier_api.py` (address deletion keeps route) |
| 2 | Atomic rider claim, one delivery per order, partner row locks | Implemented, test-verified | `InternalCourierService.accept/assign`, `test_dispatch_marketplace.py` |
| 3 | Priced jobs (suggested fare from distance, min fare) | Implemented, test-verified | `services/dispatch_pricing.py` (#125) |
| 4 | inDrive-style rider offers, expiry, seller choice | Implemented, test-verified | `services/dispatch_marketplace_service.py`, `delivery_offers` (0020) |
| 5 | Customer handover OTP, never stored, Redis attempt limit | Implemented, test-verified (hardened in phase 6, see #19) | `services/delivery_handover.py`, `POST /deliveries/{id}/delivered` |
| 6 | Consent-based foreground rider GPS, 90 s TTL, revocation, replay protection | Implemented, test-verified | `services/delivery_position.py` (#119) |
| 7 | Delivery journey milestones + live ETA labelled as estimate | Implemented, test-verified | `GET /deliveries/orders/{id}/journey` (#125) |
| 8 | Masked calling between order parties | Implemented, awaiting live provider | `services/masked_call_service.py` (#124), needs Africa's Talking account |
| 9 | Rider online/offline, verification gate | Implemented, test-verified | `PUT /delivery-partners/me/availability`, `RiderStatusCard` (#127) |
| 10 | Admin dispatch control centre | Implemented, test-verified (phase 2) | `services/dispatch_admin_service.py`, `/admin/dispatch/*`, `tests/api/test_dispatch_admin.py` |
| 11 | Rider issue reports with admin triage | Implemented, test-verified (phase 2) | OPEN → INVESTIGATING → RESOLVED (note required); auto-REROUTED on release/reassign |
| 12 | Materials vendor → tailor dispatch (Workflow B) | Implemented, test-verified (phase 1, #130) | Vendor pickup location, vendor-order requests/offers/claims, rider pickup/handover for materials, tailor receipt; `tests/api/test_materials_delivery_leg.py` |
| 13 | Vendor → tailor → customer as two traceable legs (Workflow C) | Implemented, test-verified (phase 7) | Each leg is dispatched on its own order; the customer order's journey lists its materials legs (vendor name, stage, time only); `tests/api/test_logistics_phase7.py` |
| 14 | Structured delivery event log with idempotency keys | Implemented, test-verified (phase 6) | `delivery_events` (0024): append-only, ordered by sequence, `Idempotency-Key` on pickup/drop-off, admin view; never stores codes |
| 15 | Sequential auto-offers with TTL (feature-flagged) | Implemented, test-verified (phase 3); off by default | `services/auto_dispatch_service.py`, `dispatch_job_offers` (0022), `tests/api/test_auto_dispatch.py` |
| 16 | Road-based route distance/ETA (Routes API or OSM) | Implemented, test-verified; provider off by default | `services/route_service.py` (Google Routes / OSRM, cache, breaker, labelled fallback); needs Google billing to enable. See `docs/logistics-routing.md` |
| 17 | Shareable recipient tracking link (no account) | Implemented, test-verified (phase 4) | `services/share_link_service.py`, `delivery_share_links` (0023), `tests/api/test_tracking_links.py` |
| 18 | Pickup verification (package count/reference) | Implemented, test-verified (phase 6) | Seller-held one-time pickup code (`DELIVERY_PICKUP_CODE_REQUIRED`), rider records package count, shown to buyer and at drop-off |
| 19 | Handover OTP expiry/rotation | Implemented, test-verified (phase 6) | `delivery_codes` (0024): random nonce + HMAC, 30 min expiry with auto-reissue, buyer rotation, burned on use, shared attempt limit |
| 20 | Notifications for dispatch events | Implemented, test-verified (phase 7) | Status-change notifications plus one-time "about N min away" and "has arrived" alerts from the rider's shared GPS (`services/delivery_proximity.py`, `DELIVERY_PROXIMITY_ALERTS_ENABLED`) |
| 21 | Admin reassignment / cancellation with audit | Implemented, test-verified (phase 2) | Pre-pickup only; audit log, timeline note, notifications; released rider loses trip access |
| 22 | Rider earnings ledger and payouts | Partially implemented | Fee recorded on delivery; payouts intentionally disabled (financial gate) |
| 23 | Multi-stop routing, capacity optimisation | Missing (later phase) | — |
| 24 | External carrier adapters | Missing; scaffold only | `integrations/delivery/provider.py`, no verified Nigerian provider |
| 25 | AI-assisted dispatch | Missing (later phase, after data exists) | — |
| 26 | Nigerian address fields (landmark, LGA, bus stop) | Implemented, test-verified (phase 7) | Optional LGA, landmark, nearest bus stop and instructions on locations (0025), frozen into order and dispatch snapshots, shown on the rider's trip card |
| 27 | Cross-account tracking denial | Implemented, test-verified | `test_order_tracking_read.py`, journey/position 404 tests |

## Phase plan (each phase = one PR, owner approval before merge)

| Phase | Scope | Depends on |
|---|---|---|
| 1 (#130) | Materials leg: vendor pickup location, vendor-order dispatch through the existing request/offer/claim/handover flow, rider pickup/delivery transitions for materials, tailor receipt confirmation, UI on vendor and tailor order pages | — |
| 2 (#131) | Admin dispatch actions: cancel/reassign with audit log and concurrency checks; issue resolution | 1 |
| 3 (#132) | Sequential auto-offers (feature-flagged) with TTL and reassignment via Celery | 1, 2 |
| 4 (#133) | Shareable recipient tracking tokens (hashed, scoped, expiring, rate-limited) | — |
| 5 | Road routing provider adapter (Google Routes / OSRM) with cache and honest fallback | Google billing enabled |
| 6 (#134) | Handover OTP rotation/expiry, pickup package verification, delivery event log with idempotency keys | 1 |
| 7 (this PR) | Rider approaching/arrived alerts, Nigerian address details, materials leg on the customer order | 1, 6 |
| 8+ | Multi-stop, external carriers, AI recommendations | Operational data, commercial agreements |

## Security and financial boundaries (unchanged by Phase 1)

- No payment, refund, settlement or payout code paths are touched. Delivery fees are recorded only.
- Riders still see pickup/drop-off **areas** only until assigned; exact pins and contacts after assignment.
- Masked calls cover material orders automatically (buyer, seller, assigned rider).

## Migration assessment for Phase 1

No schema change is required: `delivery_requests`, `deliveries`, `delivery_offers`
and `orders` already represent a leg per order, and vendors already have
`warehouse_location_id`. Existing customer-order behaviour is unchanged.

## Phase 3 design notes: auto-offers

- **Flag:** `DISPATCH_AUTO_OFFER_ENABLED` (default `false`). With it off, behaviour is exactly as before.
- **Eligible:** verified, online, has a vehicle, no active delivery, not already offered this job, within
  `DISPATCH_AUTO_OFFER_RADIUS_KM` when a base location is known.
- **Ranking:** straight-line km from the rider's base (current location, else KYC home address) to pickup,
  then rating, then completed deliveries; riders without a known base rank last. Distance is used for
  ranking only and is never shown as an ETA. Rider locations never leave the server.
- **Exclusive window:** `DISPATCH_AUTO_OFFER_TTL_SECONDS`. During it the job is hidden from other riders'
  board and they can't claim or bid. A partial unique index enforces one live offer per job.
- **Advance:** decline, expiry (Celery beat every 15 s, plus lazy checks on reads) or the rider going
  offline move the job to the next rider. After `DISPATCH_AUTO_OFFER_MAX_ATTEMPTS`, or with no eligible
  rider, the job stays on the open board (manual claim and fare offers still work).
- **Rollout:** enable in staging with synthetic riders first; watch acceptance and expiry rates
  on the admin board before enabling in production.

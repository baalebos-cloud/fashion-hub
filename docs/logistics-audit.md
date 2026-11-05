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
| 5 | Customer handover OTP, HMAC-derived (not stored), Redis attempt limit | Implemented, test-verified | `services/delivery_handover.py`, `POST /deliveries/{id}/delivered` |
| 6 | Consent-based foreground rider GPS, 90 s TTL, revocation, replay protection | Implemented, test-verified | `services/delivery_position.py` (#119) |
| 7 | Delivery journey milestones + live ETA labelled as estimate | Implemented, test-verified | `GET /deliveries/orders/{id}/journey` (#125) |
| 8 | Masked calling between order parties | Implemented, awaiting live provider | `services/masked_call_service.py` (#124), needs Africa's Talking account |
| 9 | Rider online/offline, verification gate | Implemented, test-verified | `PUT /delivery-partners/me/availability`, `RiderStatusCard` (#127) |
| 10 | Admin dispatch control centre | Implemented, test-verified (phase 2) | `services/dispatch_admin_service.py`, `/admin/dispatch/*`, `tests/api/test_dispatch_admin.py` |
| 11 | Rider issue reports with admin triage | Implemented, test-verified (phase 2) | OPEN → INVESTIGATING → RESOLVED (note required); auto-REROUTED on release/reassign |
| 12 | Materials vendor → tailor dispatch (Workflow B) | Implemented, test-verified (phase 1, #130) | `InternalCourierService.request` rejects `vendor_order`; vendor orders stall at `ready_for_pickup`; no vendor pickup location endpoint; tailor cannot confirm receipt |
| 13 | Vendor → tailor → customer as two traceable legs (Workflow C) | Blocked by #12 | Orders are already linked (`material_order_parent`, 0010); each order has its own request/delivery |
| 14 | Structured delivery event log with idempotency keys | Partially implemented | `OrderTimelineEntry` + `tracking_events` table (unused for status events) |
| 15 | Sequential auto-offers with TTL / auto-assignment | Missing | `DeliveryRequestService.broadcast_to_nearby_partners` raises `NotImplementedError` |
| 16 | Road-based route distance/ETA (Routes API or OSM) | Missing | Haversine × road factor only, labelled as estimate |
| 17 | Shareable recipient tracking link (no account) | Missing | — |
| 18 | Pickup verification (package count/reference) | Partially implemented | Pickup is assigned-rider only; no package-count check |
| 19 | Handover OTP expiry/rotation | Defective (low risk) | Code is deterministic per delivery, never expires (attempt-limited only) |
| 20 | Notifications for dispatch events | Partially implemented | In-app notifications on status change; no rider-approaching/ETA events |
| 21 | Admin reassignment / cancellation with audit | Implemented, test-verified (phase 2) | Pre-pickup only; audit log, timeline note, notifications; released rider loses trip access |
| 22 | Rider earnings ledger and payouts | Partially implemented | Fee recorded on delivery; payouts intentionally disabled (financial gate) |
| 23 | Multi-stop routing, capacity optimisation | Missing (later phase) | — |
| 24 | External carrier adapters | Missing; scaffold only | `integrations/delivery/provider.py`, no verified Nigerian provider |
| 25 | AI-assisted dispatch | Missing (later phase, after data exists) | — |
| 26 | Nigerian address fields (landmark, LGA, bus stop) | Partially implemented | Address model has landmark/instructions; no LGA field |
| 27 | Cross-account tracking denial | Implemented, test-verified | `test_order_tracking_read.py`, journey/position 404 tests |

## Phase plan (each phase = one PR, owner approval before merge)

| Phase | Scope | Depends on |
|---|---|---|
| **1 (this PR)** | Materials leg: vendor pickup location, vendor-order dispatch through the existing request/offer/claim/handover flow, rider pickup/delivery transitions for materials, tailor receipt confirmation, UI on vendor and tailor order pages | — |
| 2 (#131) | Admin dispatch actions: cancel/reassign with audit log and concurrency checks; issue resolution | 1 |
| 3 | Sequential auto-offers (feature-flagged) with TTL and reassignment via Celery | 1, 2 |
| 4 | Shareable recipient tracking tokens (hashed, scoped, expiring, rate-limited) | — |
| 5 | Road routing provider adapter (Google Routes / OSRM) with cache and honest fallback | Google billing enabled |
| 6 | Handover OTP rotation/expiry, pickup package verification, delivery event log with idempotency keys | 1 |
| 7+ | Multi-stop, external carriers, AI recommendations | Operational data, commercial agreements |

## Security and financial boundaries (unchanged by Phase 1)

- No payment, refund, settlement or payout code paths are touched. Delivery fees are recorded only.
- Riders still see pickup/drop-off **areas** only until assigned; exact pins and contacts after assignment.
- Masked calls cover material orders automatically (buyer, seller, assigned rider).

## Migration assessment for Phase 1

No schema change is required: `delivery_requests`, `deliveries`, `delivery_offers`
and `orders` already represent a leg per order, and vendors already have
`warehouse_location_id`. Existing customer-order behaviour is unchanged.

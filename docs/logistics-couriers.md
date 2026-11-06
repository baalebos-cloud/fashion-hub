# Outside courier companies (logistics phase 6)

## Research (November 2026)

The brief asked us to separate **courier networks**, which carry parcels, from **logistics software**,
which manages your own riders.

| Name | What it is | Merchant deliveries in Nigeria? | Status here |
|---|---|---|---|
| Uber Direct | Uber's business delivery API | No evidence of it in Nigeria. A 2026 report (unconfirmed in English) says Uber is leaving Nigeria from 2 Sept 2026 | Not viable |
| Onfleet, Bringg, Locus, FarEye | Dispatch/route software | Software only: they manage *your* fleet, which Tailora already does | Not a fit |
| **Shipbubble** | Aggregator, one API over 30+ couriers (incl. GIG, Sendbox, DHL) | Yes | Best first candidate. Needs API access from their team |
| **Sendbox** | API plus dashboard over a courier network | Yes | Candidate. Needs API access |
| **GIG Logistics (GIGGo)** | Courier with API-enabled deliveries | Yes | Candidate. Only unofficial plugin docs found, so we need official docs |

No public API reference was found for these providers. **No real adapter is built.** The brief says
to build one only where documented API access exists, and we haven't been given access to any.

Sources: [TechCabal on Shipbubble](https://techcabal.com/2023/10/26/shipbubble-wants-to-help-nigerian-e-commerce-deliver-everything-everywhere-on-time/), [Sendbox review](https://brands.ng/sendbox-nigeria-review-best-delivery-platform-for-small-businesses/), [GIGGo](https://giglogistics.com/giggo/), [report of Uber's exit](https://latele.ch/articles/uber-annonce-son-depart-du-nigeria-pays-le-plus-peuple-d-afrique).

## What's built

- **The contract** (`app/integrations/couriers/base.py`). Every adapter implements:
  - `eligible` and `quote`
  - `book` (with an idempotency key) and `cancel`
  - `status` (for reconciliation)
  - `verify_webhook` and `parse_webhook`

  Courier statuses are normalised to booked, courier_assigned, picked_up, in_transit, delivered, failed and cancelled.
- **Sandbox courier** (`sandbox.py`): a pretend courier with deterministic prices and HMAC-signed webhooks, for
  development and tests. **It's refused in production.**
- **Dispatcher flow** (Admin → Deliveries → a waiting job → **Courier companies**):
  - **Prices:** live quotes from each enabled courier.
  - **Book:** needs a reason for the audit log. It re-quotes, refuses if the price changed, and creates a delivery with
    `provider=<courier>` and no rider. If our save fails after the courier booked, the booking is cancelled with the
    courier, so nothing is left orphaned.
  - **Cancel:** only before pickup. The job goes back to waiting.
- **Status updates:** `POST /api/v1/webhooks/couriers/{courier}`.
  - The signature is checked first.
  - Each courier event is stored once (`courier_events`, migration 0030), so duplicates are ignored.
  - Progress only moves forward.
  - Orders move through the **same states as with Tailora riders**.
  - Proof of delivery is saved.
- **Reconciliation:** every 10 minutes, Celery polls couriers for unfinished deliveries, to catch lost webhooks.
- **Customers** see "Delivered by our courier partner …". Tailora riders, codes and flows are unchanged.

**Money:** the courier's price is **recorded** on the delivery for reference. Nothing here charges a customer,
pays a courier or touches payouts. Paying couriers is a separate, owner-approved decision.

## Adding a real courier (e.g. Shipbubble)

1. Get API access and webhook signing details from the courier.
2. Add `app/integrations/couriers/shipbubble.py` implementing `CourierAdapter`, mapping their statuses to ours,
   and register it in `_ADAPTERS`.
3. Contract-test it against their sandbox. The tests in `tests/api/test_courier_adapters.py` show what must hold.
4. Owner approval, then on Railway: `EXTERNAL_COURIERS=shipbubble` plus that courier's key and webhook secret.
   Give the courier the webhook URL `https://<api>/api/v1/webhooks/couriers/shipbubble`.

## Settings

| Variable | Default | Purpose |
|---|---|---|
| `EXTERNAL_COURIERS` | empty | Comma list of enabled couriers. Empty means the feature is off |
| `SANDBOX_COURIER_WEBHOOK_SECRET` | none | Signs sandbox webhooks (development only) |

## Rollback

Empty `EXTERNAL_COURIERS` switches everything off: quotes return nothing and webhooks return 404. Revert the
PR to remove the code. Migration 0030 only adds the `courier_events` table (`alembic downgrade 0029`).

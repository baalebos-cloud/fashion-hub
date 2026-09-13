# Database Schema

PostgreSQL 16 + PostGIS. Every table uses a UUID primary key
(`UUIDPrimaryKeyMixin`) and server-generated `created_at`/`updated_at`
(`TimestampMixin`) -- see `app/models/mixins.py`.

## Entity groups

**Identity**: `users`, `sessions` (refresh tokens)
**Personas**: `customers`, `professionals` (+ `tailors`, `designers`),
`vendors`, `delivery_partners`
**Catalog**: `vendor_categories`, `vendor_products`, `product_variants`,
`inventory`, `categories`, `designs`, `design_images`
**Commerce**: `carts`, `cart_items`, `orders`, `order_items`,
`order_status_definitions`, `order_timeline`
**Payments**: `payments`, `payment_transactions`, `refunds`, `invoices`,
`receipts`, `payment_consents`
**Delivery**: `delivery_partners`, `delivery_requests`, `deliveries`,
`delivery_tracking`, `tracking_events`
**Geo**: `locations` (PostGIS `geography(Point)`), `addresses`
**Fulfillment support**: `measurements`, `measurement_profiles`
**Trust**: `reviews`, `ratings`, `kyc_verifications`, `kyb_verifications`,
`verification_documents`
**Engagement**: `notifications`, `conversations`, `messages`,
`ai_conversations`, `ai_messages`, `ai_actions`, `favorites`
**Ops**: `audit_logs`

## Notable design decisions

### One `orders` table for both order types

`orders.order_type` discriminates `customer_order` vs `vendor_order`.
Both need identical infrastructure (line items, status machine, timeline,
payment, invoice, delivery), so sharing the table avoids duplicating that
plumbing. `order_service.py` and the status enums in `app/core/constants.py`
enforce which status values are valid per type.

### PostGIS `geography(Point, 4326)` on `locations.geom`

Enables `ST_DWithin`/KNN queries for "tailors near me" and nearest-partner
matching without loading every row into application memory. Precision is
truncated in `location_service.to_public_view()` before returning a
location to a user who isn't a fulfillment party on that order.

### Payment idempotency at the database layer

`payment_transactions.provider_event_id` has a **unique constraint**. This
is the durable backstop for duplicate webhook delivery -- even if the
Redis-based fast-path lock (`app/core/redis.py::acquire_idempotency_lock`)
is lost or expires, a second insert of the same `provider_event_id` raises
an `IntegrityError` that `payment_service.py` catches and treats as a no-op.

### Append-only tables

`order_timeline`, `tracking_events`, and `audit_logs` are never updated or
deleted by application code. They exist purely as historical record for
customer-facing tracking UIs, delivery route replay, and security audits.

### `orders.idempotency_key` (unique, nullable)

Client-supplied key (e.g. from a mobile app's checkout button) used to
de-duplicate order creation if a request is retried after a dropped
connection -- see the "customer loses internet connection during checkout"
edge case in `order_service.create_customer_order`.

## Migrations

Managed via Alembic (`migrations/`). The first migration
(`0001_enable_postgis_extension.py`) must run before any migration that
creates a `Geography`/`Geometry` column.

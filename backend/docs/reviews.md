# Reviews & Ratings

## Rule: review only after fulfillment

`ReviewService.create_review` enforces that `order.status` is
`RECEIVED` or `COMPLETED` before allowing a review, and that only the
order's own buyer can review it — the same
`POST /orders/{order_id}/review` route additionally duplicates a
lightweight version of this check before delegating, but the service is
the single source of truth (call it directly rather than re-deriving the
rule elsewhere).

One review per order (`Review.order_id` should carry a unique constraint
in a full migration — currently modeled via a repository-level lookup in
`ReviewService.create_review`).

## Two review relationships

- **Customer → Tailor/Designer**: on a completed customer order.
- **Tailor/Designer → Vendor**: on a completed vendor order (same service,
  different `order_type`).

## Ratings

`Rating.axis` defaults to `"overall"` but supports multi-axis ratings
(quality/communication/timeliness) without a schema migration, should that
become a product requirement later.

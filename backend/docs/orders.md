# Orders

## Endpoint reference (customer orders)

```
GET  /api/v1/orders                          list orders for the current user
GET  /api/v1/orders/{order_id}                get one order

POST /api/v1/orders/{order_id}/accept         tailor/designer accepts
POST /api/v1/orders/{order_id}/start-production
POST /api/v1/orders/{order_id}/ready          ready for delivery
POST /api/v1/orders/{order_id}/ship

GET  /api/v1/orders/{order_id}/tracking       live delivery tracking snapshot

POST /api/v1/orders/{order_id}/received       CUSTOMER ONLY -- see below

GET  /api/v1/orders/{order_id}/timeline       append-only status history

POST /api/v1/orders/{order_id}/review         CUSTOMER ONLY, after RECEIVED/COMPLETED

POST /api/v1/orders/{order_id}/cancel         additional endpoint (edge-case requirement)
```

Implemented in `app/api/v1/orders.py`, delegating all state changes to
`app/services/order_service.py::OrderService`.

## Customer order state machine

```
PENDING -> PAID -> ACCEPTED -> IN_PRODUCTION -> READY_FOR_DELIVERY
        -> SHIPPED -> OUT_FOR_DELIVERY -> DELIVERED -> RECEIVED -> COMPLETED
```

Valid transitions are defined once, in
`app/core/constants.py::CUSTOMER_ORDER_TRANSITIONS`, and enforced by
`OrderService.transition` — any transition not in that map is rejected
with `InvalidStateTransitionError` (HTTP 409), regardless of role.

## Mark as Received rule

This is a hard product requirement, enforced at the service layer (not
just via route RBAC), so it can't be bypassed even by a direct API call:

- `POST /orders/{id}/received` requires role `customer`
  (`require_roles(Role.CUSTOMER)` at the route).
- `OrderService.transition` additionally checks
  `order.buyer_user_id == actor.id` — a **different** customer, or a
  tailor/designer under any circumstance, gets a 403.
- On success, the service immediately (and separately, for a clean audit
  trail) transitions `RECEIVED -> COMPLETED`.

## Ownership rule for professionals

`OrderService.transition` checks, for any tailor/designer actor, that
`order.seller_user_id == actor.id` before allowing `/accept`,
`/start-production`, `/ready`, `/ship`. A tailor attempting to modify
another tailor's order gets a 403 (`ForbiddenError`), covering the
"tailor attempts to modify another tailor's order" edge case explicitly.

## Idempotent order creation

`OrderService.create_customer_order` accepts an optional
`idempotency_key`. If the same key is submitted twice (e.g. the client
retried after losing connectivity mid-checkout), the existing order is
returned instead of creating a duplicate — see
`orders.idempotency_key` (unique) in [database.md](./database.md).

## Cancellation

`OrderService.cancel` rejects cancellation once an order has reached
`SHIPPED` or later — at that point, use a refund request instead (see
[payments.md](./payments.md)).

## Vendor order state machine

See [vendors.md](./vendors.md#order-handling).

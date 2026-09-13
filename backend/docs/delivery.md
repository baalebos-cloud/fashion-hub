# Delivery

## Provider abstraction

```
DeliveryProvider (ABC)             app/integrations/delivery/base.py
└── InternalDeliveryProvider       app/integrations/delivery/provider.py (default)
```

`InternalDeliveryProvider` is the default: it matches orders to the
platform's own registered delivery partners rather than calling an
external courier API, so the platform can operate on day one without a
third-party delivery contract. Add external couriers later by implementing
`DeliveryProvider` and registering them in
`app/integrations/delivery/__init__.py` — business logic never changes.

## Flow

1. Order reaches `READY_FOR_DELIVERY` (customer order) or
   `READY_FOR_PICKUP` (vendor order).
2. `DeliveryRequestService.create_for_order` creates a `DeliveryRequest`
   and enqueues `broadcast_delivery_request_task` (Celery) to notify
   nearby **available** delivery partners (PostGIS proximity query —
   see [maps-and-gps.md](./maps-and-gps.md)).
3. A partner accepts (`DeliveryRequestService.accept`) → creates a
   `Delivery` row.
4. Partner updates status through pickup → in transit → delivered
   (`DeliveryService.mark_picked_up`, `mark_delivered`).

## Edge case: delivery partner rejects a delivery

`DeliveryRequestService.reject` resets the request's status back to
`requested` (not a terminal failure) and re-broadcasts to the next-nearest
partner, recording the rejection reason for audit.

## Edge case: delivery fails

Model this as `Delivery.status = 'failed'` with a `TrackingEvent` of type
`exception` recording why; trigger a customer/support notification and
allow the order to route to a refund/re-delivery decision rather than
silently stalling.

## Proof of delivery

`Delivery.proof_of_delivery_url` — set via `DeliveryService.mark_delivered`
with a photo URL uploaded through the storage integration.

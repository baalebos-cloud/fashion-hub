# Customers

`Customer` (1:1 with `User`, role=`customer`) stores customer-specific
preferences (default measurement profile, preferred currency). Addresses
are stored in `Address` (labeled pointer to a `Location`), and body
measurements in `MeasurementProfile` + `Measurement`.

## Key flows

- **Browse professionals**: `GET /api/v1/professionals` (search/filter by
  verification status, garment specialties, location radius).
- **View a profile**: portfolio (`DesignImage`), designs/services
  (`Design`), pricing, and aggregate rating (`Professional.average_rating`).
- **Place an order**: see [orders.md](./orders.md).
- **Track**: `GET /api/v1/orders/{order_id}/tracking`.
- **Mark received**: `POST /api/v1/orders/{order_id}/received` — only the
  customer who placed the order can call this; see
  [orders.md](./orders.md#mark-as-received-rule).
- **Review**: `POST /api/v1/orders/{order_id}/review` — only after
  `RECEIVED`/`COMPLETED`.

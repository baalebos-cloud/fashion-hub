# Professional (Tailor/Designer) Flow

## Customer-order side

`pages/professional/Orders.tsx` -> `OrderDetails.tsx`, using
`components/orders/OrderActions.tsx` to expose exactly the one action
valid for the order's current status: Accept -> Start Production ->
Mark Ready -> Ship. The professional can never call "Mark as Received" —
that button is customer-only (see `components/orders/MarkReceivedButton.tsx`
and `backend/docs/orders.md#mark-as-received-rule`).

## Material-supply side

```
Vendor Marketplace -> browse Fabric/Buttons/Zippers/Thread/Accessories
  -> Cart (may span multiple vendors) -> One Checkout -> Payment
  -> Invoice -> Vendor Processes -> Delivery Partner
  -> Tailor/Designer Location -> Received
```

`pages/professional/VendorMarketplace.tsx` -> `Cart.tsx` -> `Checkout.tsx`
produces one Order per vendor but a single combined payment (see
`backend/docs/checkout.md`). `VendorOrders.tsx` is where the professional,
as the BUYER this time, gets their own "Mark as Received" affordance on
each vendor order.

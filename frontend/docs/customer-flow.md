# Customer Flow

```
Find Tailor/Designer -> Select Professional -> Design + Measurements
  -> Delivery Location -> Checkout -> Payment
  -> Invoice + Order Created -> Tailor/Designer -> Production
  -> Ready to Send -> Delivery Partner -> Tracking Map -> Delivered
  -> Customer Receives -> Mark as Received -> Review
```

## Pages involved, in order

1. `pages/customer/FindProfessionals.tsx`
2. `pages/customer/ProfessionalDetails.tsx`
3. `pages/customer/CreateOrder.tsx` (design + measurements + delivery
   location, via `components/checkout/MapLocationPicker.tsx`)
4. `pages/customer/Checkout.tsx` -> `pages/customer/Payment.tsx`
5. `pages/customer/PaymentSuccess.tsx` (backend has independently verified
   the payment by this point — see `backend/docs/payments.md`)
6. `pages/customer/OrderDetails.tsx` — professional-side status updates
   arrive here via polling/refetch as the order moves through
   `accepted -> in_production -> ready_for_delivery -> shipped`
7. `pages/customer/TrackOrder.tsx` — live map once a delivery exists
8. Back to `OrderDetails.tsx` once `delivered` —
   `components/orders/MarkReceivedButton.tsx` appears, customer-only
9. `components/reviews/ReviewForm.tsx` — only renders once
   `status` is `received`/`completed`

Every status transition shown in the UI is read from the backend's
response to the corresponding action call
(`api/orders.api.ts`) — the frontend never advances a status locally.

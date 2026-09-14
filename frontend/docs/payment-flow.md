# Payment Flow

1. `components/payments/PaymentButton.tsx` calls
   `hooks/use-payment.ts::payAndRedirect`, which hits
   `POST /payments` then redirects the browser to the provider's hosted
   page. No payment UI is rendered in this app itself.
2. The provider redirects back to a callback route
   (`pages/customer/PaymentSuccess.tsx` / `PaymentFailed.tsx`).
3. That page calls `paymentsApi.verify()` as a belt-and-suspenders check —
   but the order is only ever actually marked paid by the backend's own
   webhook-driven, signature-verified confirmation
   (see `backend/docs/payments.md`). This frontend call never flips
   anything client-side; it just re-fetches the now-authoritative order.

**The frontend never decides a payment succeeded.** It only ever displays
whatever status the backend reports.

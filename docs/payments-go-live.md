# Turning on payments (Paystack)

Checkout, payment confirmation, Paystack's webhook, order updates, seller payout records, invoices and
notifications are built and tested. They stay off until the steps below are done. Steps marked
**Owner** need your accounts, keys or production settings.

## 1. Test end to end first (test keys, local)

1. **Owner:** in the Paystack dashboard (test mode), copy the test secret and public keys.
2. Put them in your local `backend/.env` (never commit it):
   ```
   PAYMENT_PROVIDER=paystack
   PAYMENT_SECRET_KEY=sk_test_…
   PAYMENT_PUBLIC_KEY=pk_test_…
   ```
3. Run the backend, a worker (`celery -A app.workers.celery_app worker -Q payments,invoices,notifications,celery`)
   and the website, then pay for an order with one of [Paystack's test cards](https://paystack.com/docs/payments/test-payments/).
4. Check: the order moves to *paid*, the seller payout is recorded as *pending*, the invoice and
   notifications appear, and paying the same order again is refused.

## 2. Go live

1. **Owner:** Paystack account activated for live payments (Paystack verifies the business: CAC
   documents, director ID, settlement bank account).
2. **Owner:** Railway (backend) environment:
   ```
   PAYMENT_PROVIDER=paystack
   PAYMENT_SECRET_KEY=sk_live_…
   PAYMENT_PUBLIC_KEY=pk_live_…
   PAYMENTS_ENABLED=true
   ```
   Paystack signs its webhooks with the secret key, so `PAYMENT_WEBHOOK_SECRET` isn't needed for it.
   Keep `REFUND_EXECUTION_ENABLED=false` and `ENABLE_PRODUCTION_PAYMENTS=false` (a separate, unfinished
   payment flow; the backend refuses to start if it is on).
3. **Owner:** Paystack dashboard → Settings → API Keys & Webhooks → Live webhook URL:
   `https://fashion-hub-production-2661.up.railway.app/api/v1/payments/webhooks/paystack`
4. **Owner:** make sure Railway runs one worker for the `payments` queue (and one beat scheduler).
   Without it, payments still settle, but invoices and notifications wait until a worker runs.
5. `CORS_ALLOWED_ORIGINS` must include the website (`https://fashion-hub-tawny.vercel.app`). It does
   today; payment return addresses are only accepted from these origins.
6. Make one small real payment and refund it by hand in the Paystack dashboard.

## Seller payouts (automatic)

Every paid order records the seller's share after the platform fee (15%). Once the **customer confirms
receipt**, a background job (every 5 minutes) sends it to the seller's bank account through **Paystack
Transfers**, unless something blocks it, in which case it's put **on hold** with the reason:

- a refund on the order is requested, approved or done, or a delivery problem is still open;
- the seller hasn't added a bank account, or the bank's account name doesn't match their verified NIN
  name or business name (an admin checks and releases);
- the seller's account is closed, or an admin held it.

Sellers add their bank account under **Payments**. The bank checks it and returns the account name; adding
or changing it needs their password, and they're notified. Account numbers are encrypted.

Admins see every payout under **Admin › Payouts**: hold one with a reason, or release a held/failed one
(needs a code from the authenticator app). Paystack reports each transfer by webhook
(`transfer.success` / `failed` / `reversed`, same webhook URL as payments); transfers it hasn't reported
after 30 minutes are checked with Paystack directly. A transfer is never sent twice.

To switch on (**Owner**, after payments work):
1. Paystack dashboard → Settings → Preferences: turn **off** "Confirm transfers before sending" (OTP),
   otherwise every transfer fails with an OTP message.
2. Keep enough money in the Paystack balance for payouts (transfers come from the balance).
3. Railway: `PAYOUTS_ENABLED=true` (and run the worker + beat scheduler, see above).
4. Test with Paystack test keys first: a test transfer to a test bank account.

## What stays manual

- **Refunds:** approved refunds are recorded but not sent to Paystack automatically
  (`REFUND_EXECUTION_ENABLED=false`); issue them in the Paystack dashboard.

## Phone apps

In the iPhone and Android apps, Paystack's page opens in the phone's browser. After paying, Paystack
returns to `https://<site>/payment/app-return`, which reopens the app on the payment result
(`tailora://app/...`). The app then confirms the payment with the backend; the webhook confirms it
either way. Set `VITE_PUBLIC_SITE_URL` when building the apps if the website address changes.

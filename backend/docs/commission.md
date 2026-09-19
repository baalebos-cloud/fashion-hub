# Platform Commission (15%)

## The rule

`PLATFORM_COMMISSION_RATE` (default 0.15) is deducted from what a
professional/vendor **nets**, never added on top of what the customer
pays. The professional/vendor's quoted price to the customer is assumed
to already have this negotiated in at onboarding -- this backend doesn't
compute or inject a markup into `Order.total_amount` anywhere.

## Where it lives

`PayoutService.create_for_order`, called once from
`payment_service.py` right after a payment is confirmed (same moment as
invoice generation and referral qualification). Writes one `Payout` row
per order: `gross_amount` (= `Order.total_amount`), `commission_rate`,
`commission_amount`, `net_amount`.

## Why the customer never sees it -- structurally, not just by permission

- `InvoiceService.generate_for_order` builds the customer's invoice from
  `Order` fields alone; it has no import of `Payout` or
  `PayoutService` anywhere in its call graph.
- `GET /payments/payouts` (the only endpoint that ever returns
  `commission_rate`/`commission_amount`) is restricted to
  `tailor | designer | vendor | admin` via `require_roles` -- a customer
  hitting it gets a 403, not an empty list. See
  `api/v1/payments.py::list_my_payouts`.

If you're auditing this for a compliance review: search the codebase for
importers of `app.models.payout` -- as of this writing, only
`payout_service.py` and `api/v1/payments.py` import it, which is the
entire surface area where commission figures can possibly reach a
response body.

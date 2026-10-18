# Invoices and receipts

After server-side payment verification, settlement commits durable outbox work
with the payment and order transition. The outbox worker calls
`InvoiceService.generate_for_order` in its transaction, producing one invoice
per order with saved line-item prices. Repeated delivery does not produce a
second invoice. See [payment recovery](../../docs/payment-recovery.md).

`GET /api/v1/invoices/by-order/{order_id}` and `GET /api/v1/invoices/{invoice_id}`
authorize the order's buyer, seller or an admin. An invoice that is still being
prepared returns 404 with a retry message. Ordinary customer invoice responses
do not expose seller commission.

`InvoiceService.render_pdf` remains unimplemented. The unused WeasyPrint
installation and its system libraries were removed during dependency
remediation. Implement and review a renderer's resource-fetch policy, storage,
access control and delivery retries before enabling PDF downloads; the current
application provides the invoice's database snapshot independently.

The receipt service remains separate and is not a completed HTTP user journey.

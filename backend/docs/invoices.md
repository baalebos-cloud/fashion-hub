# Invoices & Receipts

## Generation

Triggered automatically by `PaymentService._apply_verified_result` on
successful payment, via the background task
`generate_invoice_for_order_task` — never inline in the webhook/callback
request path, so the provider gets a fast HTTP response.

`InvoiceService.generate_for_order` snapshots line items (`name`,
`unit_price`, `quantity`, `line_total`) into `Invoice.line_items_snapshot`
(JSONB) at generation time, so the invoice remains accurate even if catalog
prices change afterward.

## PDF rendering

`InvoiceService.render_pdf` (stubbed — wire in WeasyPrint, already listed
in `requirements.txt`, against `app/templates/invoices/invoice.html`) then
uploads via the configured `StorageProvider` and emails both parties
(`send_invoice_email_task`).

## Access control

- Customer orders: visible to the **customer** and the **tailor/designer**.
- Vendor orders: visible to the **tailor/designer (buyer)** and the
  **vendor (seller)**.
- Admins can view all invoices.

Enforce this in the `invoices.py` route (currently a scaffold stub) using
the same `_assert_can_view_order`-style pattern as `orders.py`.

## Receipts

`ReceiptService.generate_for_payment` creates a `Receipt` tied to the
`Invoice` + `Payment`, confirming the amount actually paid (distinct from
the invoice, which itemizes what was purchased).

# Checkout

`CheckoutService.checkout_cart` implements the spec requirement: a cart may
span multiple vendors, but the buyer pays **once** and gets **one**
checkout/payment record, while each vendor still gets their own `Order`
(and invoice) for their own accounting.

## Algorithm

1. Load all `CartItem`s for the cart.
2. Lock every referenced `Inventory` row via `SELECT ... FOR UPDATE`, **in a
   stable sorted order by `product_variant_id`** — this prevents deadlocks
   when two concurrent checkouts touch overlapping products.
3. Re-verify `quantity_available >= requested quantity` for every item.
   Any shortfall fails the **entire** checkout with an itemized error
   (never a silent partial fulfillment).
4. Group line items by `vendor_id`; create one `Order`
   (`order_type='vendor_order'`) per vendor, all sharing an
   `idempotency_key` prefix (`{checkout_group_key}:{vendor_id}`) so the
   payment layer can charge them together as a single transaction.
5. Decrement `quantity_available` / increment `quantity_reserved` for each
   item, inside the same DB transaction as order creation.
6. Mark the cart `checked_out`.

## Edge case: oversell protection

Because steps 2–5 happen inside one transaction with row locks acquired in
a consistent order, two customers racing to buy the last unit of a fabric
can never both succeed — the second transaction blocks on the lock, then
sees the updated (now insufficient) `quantity_available` and fails cleanly
with a `ConflictError` listing exactly which items are short.

## Single payment across vendor orders

The client receives all created `Order`s from checkout, sums their
`total_amount`, and calls `POST /api/v1/payments` once with that combined
total against a single "checkout group" payment record. On success,
`PaymentService` marks each underlying vendor order paid — a full
implementation should extend `Payment` with a `checkout_group_key` FK so
that one webhook event fans out to all sibling orders atomically.

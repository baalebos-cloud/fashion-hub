# Cart

`Cart` + `CartItem` support a tailor/designer adding products from
**multiple vendors** into one cart before a single checkout.

## Stock checking: two layers

1. **Soft check at add-to-cart time** (`CartService.add_item`) — rejects
   obviously-oversized additions for good UX, but does **not** reserve
   inventory. Reserving at add-time would let idle carts starve other
   buyers of stock that was never going to be purchased.
2. **Hard, atomic check at checkout time** (`CheckoutService.checkout_cart`)
   — the authoritative check. See [checkout.md](./checkout.md).

## Endpoints (scaffold: `app/api/v1/carts.py`)

Wire in against `CartService`:
- Add item, update quantity, remove item
- Get cart summary (subtotal, item list)

## Edge case: vendor sells out while item sits in cart

Handled entirely at checkout time with a row-locked, transactional
inventory decrement — see [checkout.md](./checkout.md#edge-case-oversell-protection).

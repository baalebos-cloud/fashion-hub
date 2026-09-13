# Tailors & Fashion Designers

`Professional` holds fields shared by both personas (bio, years of
experience, shop photo, location, verification badge, rating). `Tailor` and
`Designer` each extend it 1:1 with type-specific fields (garment
specialties/turnaround time vs. style tags/signature collection).

## Verification

`Professional.is_verified` is derived from a `KYBVerification` (business)
and/or `KYCVerification` (individual) reaching `VerificationStatus.VERIFIED`
— see [kyc-kyb.md](./kyc-kyb.md). Unverified professionals can still create
a profile but should be excluded from default search results and clearly
marked as unverified where shown.

## Order handling

A professional receives orders where `orders.seller_user_id == their user
id` and `order_type = 'customer_order'`. See [orders.md](./orders.md) for
the full lifecycle and the rule that professionals can never mark an order
`RECEIVED`.

## Vendor marketplace access

Professionals shop for materials via the same account
(`GET /api/v1/vendor-products`, `POST /api/v1/carts`, ...) — see
[cart.md](./cart.md) and [checkout.md](./checkout.md).

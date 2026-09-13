# Vendors

`Vendor` (1:1 with `User`, role=`vendor`) sells materials (fabrics,
buttons, zippers, threads, etc.) to tailors/designers through
`VendorProduct` + `ProductVariant` + `Inventory`.

## Product management

- `POST /api/v1/vendor-products` — creates a product with a default
  variant and zero-quantity inventory row (`ProductService.create_product`).
- Vendors add real SKUs/variants (e.g. different colors/units) and set
  stock via `POST /api/v1/vendor-inventory` (`InventoryService.restock`).

## Order handling

A vendor receives orders where `orders.seller_user_id == their user id`
and `order_type = 'vendor_order'`, created via the checkout flow — see
[checkout.md](./checkout.md). Vendor order lifecycle:

```
CART -> CHECKOUT -> PAYMENT_PENDING -> PAID -> CONFIRMED -> PROCESSING
     -> READY_FOR_PICKUP -> PICKED_UP -> IN_TRANSIT -> DELIVERED
     -> RECEIVED -> COMPLETED
```

Only the buyer (tailor/designer) may transition `DELIVERED -> RECEIVED`,
mirroring the customer-order rule.

## Verification

Vendors require KYB verification before receiving the verified badge — see
[kyc-kyb.md](./kyc-kyb.md).

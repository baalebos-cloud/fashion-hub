# Vendor Flow

`pages/vendor/Products.tsx` / `AddProduct.tsx` / `Inventory.tsx` manage the
catalog; `pages/vendor/Orders.tsx` -> `OrderDetails.tsx` handles incoming
vendor orders through `confirmed -> processing -> ready_for_pickup`. Once
picked up, the vendor's role in that order is done — delivery and receipt
confirmation belong to the delivery partner and the buying professional
respectively.

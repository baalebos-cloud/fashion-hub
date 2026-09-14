import { CartItem } from "./CartItem";
import { EmptyCart } from "./EmptyCart";
import type { CartItem as CartItemType } from "@/types/cart";

export function CartList({ items }: { items: CartItemType[] }) {
  if (items.length === 0) return <EmptyCart />;

  // Group by vendor, per backend/docs/cart.md — a checkout may span
  // multiple vendors, so show that structure here too.
  const groups = items.reduce<Record<string, CartItemType[]>>((acc, item) => {
    (acc[item.vendor_id] ??= []).push(item);
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      {Object.entries(groups).map(([vendorId, vendorItems]) => (
        <div key={vendorId}>
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-soft">Vendor {vendorId.slice(0, 8)}</div>
          {vendorItems.map((item) => (
            <CartItem key={item.id} item={item} />
          ))}
        </div>
      ))}
    </div>
  );
}

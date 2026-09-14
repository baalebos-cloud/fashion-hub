import { QuantityControl } from "./QuantityControl";
import { formatCurrency } from "@/lib/formatters/currency";
import { useCart } from "@/hooks/use-cart";
import type { CartItem as CartItemType } from "@/types/cart";

export function CartItem({ item }: { item: CartItemType }) {
  const { removeItem } = useCart();

  return (
    <div className="flex items-center justify-between border-b border-line py-3 last:border-0">
      <div>
        <div className="text-sm text-ink">Item {item.product_variant_id.slice(0, 8)}</div>
        <div className="text-xs text-ink-soft">{formatCurrency(item.unit_price_snapshot)} each</div>
      </div>
      <div className="flex items-center gap-4">
        <QuantityControl cartItemId={item.id} quantity={item.quantity} />
        <button onClick={() => removeItem(item.id)} className="text-xs text-thread hover:underline" aria-label="Remove item">
          Remove
        </button>
      </div>
    </div>
  );
}

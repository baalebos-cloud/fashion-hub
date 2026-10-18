import { QuantityControl } from "./QuantityControl";
import { formatCurrency } from "@/lib/formatters/currency";
import { useState } from "react";
import { useCartStore } from "@/store/cart.store";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { CartItem as CartItemType } from "@/types/cart";

export function CartItem({ item }: { item: CartItemType }) {
  const removeItem = useCartStore((state) => state.removeItem);
  const [error, setError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  async function remove() {
    setRemoving(true); setError(null);
    try { await removeItem(item.id); }
    catch (err) { setError(getDisplayErrorMessage(err)); }
    finally { setRemoving(false); }
  }

  return (
    <div className="flex items-center justify-between border-b border-line py-3 last:border-0">
      <div>
        <div className="text-sm text-ink">{item.product_name}</div>
        <div className="text-xs text-ink-soft">{formatCurrency(item.unit_price_snapshot, item.currency)} each</div>
        {!item.is_available && <p className="text-xs text-thread">Unavailable; update or remove this item.</p>}
        {error && <p role="alert">{error}</p>}
      </div>
      <div className="flex items-center gap-4">
        <QuantityControl cartItemId={item.id} quantity={item.quantity} />
        <button disabled={removing} onClick={() => { void remove(); }} className="text-xs text-thread hover:underline" aria-label="Remove item">
          Remove
        </button>
      </div>
    </div>
  );
}

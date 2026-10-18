import { useState } from "react";
import { useCartStore } from "@/store/cart.store";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function QuantityControl({ cartItemId, quantity }: { cartItemId: string; quantity: number }) {
  const updateItem = useCartStore((state) => state.updateItem);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function commit(next: number) {
    setIsSaving(true); setError(null);
    try { await updateItem(cartItemId, next); }
    catch (err) { setError(getDisplayErrorMessage(err)); }
    finally { setIsSaving(false); }
  }
  return <div>
    <div className="inline-flex items-center rounded-lg border border-line">
      <button type="button" aria-label="Decrease quantity" onClick={() => { void commit(quantity - 1); }} disabled={isSaving || quantity <= 1} className="h-8 w-8">−</button>
      <span className="w-8 text-center text-sm">{quantity}</span>
      <button type="button" aria-label="Increase quantity" onClick={() => { void commit(quantity + 1); }} disabled={isSaving || quantity >= 10000} className="h-8 w-8">+</button>
    </div>
    {error && <p role="alert" className="text-xs text-thread">{error}</p>}
  </div>;
}

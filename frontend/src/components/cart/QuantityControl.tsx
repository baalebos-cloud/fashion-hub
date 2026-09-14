import { useState } from "react";
import { useCart } from "@/hooks/use-cart";

export function QuantityControl({ cartItemId, quantity }: { cartItemId: string; quantity: number }) {
  const { updateItem } = useCart();
  const [value, setValue] = useState(quantity);
  const [isSaving, setIsSaving] = useState(false);

  async function commit(next: number) {
    if (next < 1) return;
    setValue(next);
    setIsSaving(true);
    try {
      await updateItem(cartItemId, next);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="inline-flex items-center rounded-lg border border-line">
      <button type="button" onClick={() => commit(value - 1)} disabled={isSaving} className="flex h-8 w-8 items-center justify-center text-ink hover:bg-muslin disabled:opacity-40">
        −
      </button>
      <span className="w-8 text-center text-sm text-ink">{value}</span>
      <button type="button" onClick={() => commit(value + 1)} disabled={isSaving} className="flex h-8 w-8 items-center justify-center text-ink hover:bg-muslin disabled:opacity-40">
        +
      </button>
    </div>
  );
}

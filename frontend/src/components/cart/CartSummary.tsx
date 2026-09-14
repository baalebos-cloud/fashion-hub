import { formatCurrency } from "@/lib/formatters/currency";

export function CartSummary({ subtotal, deliveryFee = 0 }: { subtotal: number; deliveryFee?: number }) {
  return (
    <div className="flex flex-col gap-2 rounded-card border border-line p-4">
      <div className="flex justify-between text-sm text-ink-soft">
        <span>Subtotal</span>
        <span>{formatCurrency(subtotal)}</span>
      </div>
      <div className="flex justify-between text-sm text-ink-soft">
        <span>Delivery</span>
        <span>{deliveryFee > 0 ? formatCurrency(deliveryFee) : "Calculated at checkout"}</span>
      </div>
      <div className="flex justify-between border-t border-line pt-2 font-medium text-ink">
        <span>Total</span>
        <span>{formatCurrency(subtotal + deliveryFee)}</span>
      </div>
    </div>
  );
}

import { formatCurrency } from "@/lib/formatters/currency";

export function PaymentSummary({ orderNumber, amount, currency }: { orderNumber: string; amount: number; currency: string }) {
  return (
    <div className="rounded-card border border-line p-4">
      <div className="text-sm text-ink-soft">Order {orderNumber}</div>
      <div className="mt-1 text-2xl font-medium text-ink">{formatCurrency(amount, currency)}</div>
    </div>
  );
}

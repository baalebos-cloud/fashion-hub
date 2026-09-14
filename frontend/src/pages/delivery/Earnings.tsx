import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";

export default function Earnings() {
  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Earnings</h1>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <Card><div className="text-xs text-ink-soft">Today</div><div className="mt-1 text-xl font-medium text-ink">{formatCurrency(0)}</div></Card>
        <Card><div className="text-xs text-ink-soft">This week</div><div className="mt-1 text-xl font-medium text-ink">{formatCurrency(0)}</div></Card>
        <Card><div className="text-xs text-ink-soft">This month</div><div className="mt-1 text-xl font-medium text-ink">{formatCurrency(0)}</div></Card>
      </div>
    </div>
  );
}

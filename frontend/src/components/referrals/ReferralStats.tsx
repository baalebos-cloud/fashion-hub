import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import type { ReferralSummary } from "@/types/referral";

export function ReferralStats({ summary }: { summary: ReferralSummary }) {
  const cards = [
    { label: "People referred", value: summary.total_referred },
    { label: "Qualified", value: summary.qualified_count },
    { label: "Total earned", value: formatCurrency(summary.total_earned) },
    { label: "Paid out", value: formatCurrency(summary.total_paid) },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <div className="text-xs text-ink-soft">{card.label}</div>
          <div className="mt-1 text-xl font-medium text-ink">{card.value}</div>
        </Card>
      ))}
    </div>
  );
}

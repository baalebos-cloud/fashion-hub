import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Design } from "@/types/design";

export function DesignCard({ design, onSelect }: { design: Design; onSelect?: () => void }) {
  return (
    <Card
      className={onSelect ? "cursor-pointer transition-colors hover:border-brass" : undefined}
      onClick={onSelect}
    >
      <div className="font-medium text-ink">{design.title}</div>
      {design.description && <p className="mt-1 line-clamp-2 text-sm text-ink-soft">{design.description}</p>}
      <div className="mt-2 font-medium text-ink">{formatCurrency(design.base_price)}</div>
    </Card>
  );
}

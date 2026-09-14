import { formatCurrency } from "@/lib/formatters/currency";
import { Button } from "@/components/ui/button";
import type { Design } from "@/types/design";

export function DesignDetails({ design, onOrder }: { design: Design; onOrder?: () => void }) {
  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">{design.title}</h1>
      {design.description && <p className="text-sm text-ink-soft">{design.description}</p>}
      <div className="text-lg font-medium text-ink">{formatCurrency(design.base_price)}</div>
      {onOrder && <Button onClick={onOrder} className="self-start">Order this design</Button>}
    </div>
  );
}

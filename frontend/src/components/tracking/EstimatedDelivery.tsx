import { formatEtaMinutes } from "@/lib/formatters/time";

export function EstimatedDelivery({ etaMinutes }: { etaMinutes: number }) {
  return (
    <div className="text-sm text-ink-soft">
      Arriving in <span className="font-medium text-ink">{formatEtaMinutes(etaMinutes)}</span>
    </div>
  );
}

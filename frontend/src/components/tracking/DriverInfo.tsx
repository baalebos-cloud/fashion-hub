import { Avatar } from "@/components/ui/avatar";
import type { DeliveryPartner } from "@/types/delivery";

export function DriverInfo({ partner, name }: { partner: DeliveryPartner; name: string }) {
  return (
    <div className="flex items-center gap-3 rounded-card border border-line p-3">
      <Avatar name={name} size="sm" />
      <div>
        <div className="text-sm font-medium text-ink">{name}</div>
        <div className="text-xs text-ink-soft">{partner.vehicle_type ?? "Delivery partner"} · ★ {partner.average_rating.toFixed(1)}</div>
      </div>
    </div>
  );
}

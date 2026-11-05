import { Avatar } from "@/components/ui/avatar";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import type { Delivery } from "@/types/delivery";

const VEHICLE_LABEL: Record<string, string> = { bike: "Motorbike", car: "Car", van: "Van", foot: "On foot" };

/** Who is bringing the order: shown to the customer before handover. First name only. */
export function RiderCard({ delivery }: { delivery: Delivery }) {
  const firstName = (delivery.rider_name ?? "").trim().split(" ")[0] || "Your rider";
  const vehicle = delivery.rider_vehicle_type ? VEHICLE_LABEL[delivery.rider_vehicle_type] ?? delivery.rider_vehicle_type : null;
  const details = [
    vehicle,
    typeof delivery.rider_rating === "number" && delivery.rider_rating > 0 ? `★ ${delivery.rider_rating.toFixed(1)}` : null,
    typeof delivery.rider_completed_deliveries === "number" ? `${delivery.rider_completed_deliveries} deliveries` : null,
  ].filter(Boolean);
  return (
    <div className="flex items-center gap-3 rounded-lg bg-muslin p-3" aria-label="Assigned rider">
      <Avatar name={firstName} src={delivery.rider_photo_url} />
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-ink">{firstName}</span>
          {delivery.rider_verified
            ? <VerificationBadge />
            : <span className="text-[11px] text-thread">Not verified</span>}
        </div>
        {details.length > 0 && <p className="text-xs text-ink-soft">{details.join(" · ")}</p>}
      </div>
    </div>
  );
}

import { formatAddressLine } from "@/lib/formatters/address";
import type { GeoLocation } from "@/types/location";

export function PickupDetails({ location, contactName, contactPhone }: { location: GeoLocation; contactName?: string; contactPhone?: string }) {
  return (
    <div className="rounded-card border border-line p-4">
      <div className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-soft">Pickup</div>
      <div className="text-sm text-ink">{formatAddressLine(location)}</div>
      {contactName && <div className="mt-1 text-sm text-ink-soft">{contactName}{contactPhone ? ` · ${contactPhone}` : ""}</div>}
    </div>
  );
}

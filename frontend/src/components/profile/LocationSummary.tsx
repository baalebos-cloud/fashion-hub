import { formatAddressLine } from "@/lib/formatters/address";
import type { GeoLocation } from "@/types/location";

export function LocationSummary({ location }: { location: GeoLocation | null }) {
  if (!location) return <p className="text-sm text-ink-soft">No location set yet.</p>;

  return (
    <div className="flex items-start gap-2 text-sm text-ink">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="mt-0.5 flex-shrink-0 text-ink-soft" aria-hidden="true">
        <path
          d="M12 21s-7-6.5-7-11a7 7 0 1114 0c0 4.5-7 11-7 11z"
          stroke="currentColor"
          strokeWidth="1.7"
        />
        <circle cx="12" cy="10" r="2.3" stroke="currentColor" strokeWidth="1.7" />
      </svg>
      <span>{formatAddressLine(location)}</span>
    </div>
  );
}

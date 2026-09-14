import { LocationSummary } from "@/components/profile/LocationSummary";
import type { GeoLocation } from "@/types/location";

export function ProfessionalLocation({ location }: { location: GeoLocation | null }) {
  return (
    <div>
      <h2 className="mb-3 text-sm font-medium text-ink-soft">Shop location</h2>
      <LocationSummary location={location} />
    </div>
  );
}

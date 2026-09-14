import { useState } from "react";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { LocationSummary } from "@/components/profile/LocationSummary";
import { useLocation } from "@/hooks/use-location";
import type { GeoLocation } from "@/types/location";

export default function Location() {
  const { saveLocation } = useLocation();
  const [saved, setSaved] = useState<GeoLocation | null>(null);

  return (
    <div className="max-w-md">
      <h1 className="mb-6 font-display text-xl text-ink">Shop location</h1>
      <LocationSummary location={saved} />
      <div className="mt-4">
        <MapLocationPicker
          onSelect={async (location) => {
            const result = await saveLocation({ ...location, locationType: "tailor_shop" });
            setSaved(result);
          }}
        />
      </div>
    </div>
  );
}

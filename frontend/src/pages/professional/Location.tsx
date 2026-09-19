import { useState, type ComponentProps } from "react";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { LocationSummary } from "@/components/profile/LocationSummary";
import { professionalsApi } from "@/api/professionals.api";
import { useToast } from "@/components/ui/toast";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { GeoLocation } from "@/types/location";

export default function Location() {
  const { showToast } = useToast();
  const [saved, setSaved] = useState<Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country"> | null>(null);

  async function handleSelect(location: Parameters<ComponentProps<typeof MapLocationPicker>["onSelect"]>[0]) {
    try {
      await professionalsApi.updateMyLocation({
        latitude: location.latitude,
        longitude: location.longitude,
        formattedAddress: location.formatted_address ?? undefined,
      });
      setSaved(location);
      showToast("Business location saved.", "success");
    } catch (err) {
      showToast(getDisplayErrorMessage(err, "Couldn't save your location."), "error");
    }
  }

  return (
    <div className="max-w-md">
      <h1 className="mb-6 font-display text-xl text-ink">Shop location</h1>
      <p className="mb-4 text-sm text-ink-soft">
        Pick your shop or workspace on the map — this is what customers use to find you and what delivery partners use for pickup.
      </p>
      {saved && <LocationSummary location={saved} />}
      <div className="mt-4">
        <MapLocationPicker onSelect={handleSelect} />
      </div>
    </div>
  );
}

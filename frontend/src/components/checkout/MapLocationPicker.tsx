import { useState } from "react";
import { useMap } from "@/hooks/use-map";
import { useGeolocation } from "@/hooks/use-geolocation";
import { reverseGeocode } from "@/lib/maps/geocoding";
import { Button } from "@/components/ui/button";
import type { GeoLocation } from "@/types/location";

export interface MapLocationPickerProps {
  onSelect: (location: Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">) => void;
}

/** Placeholder map surface with a "use my location" affordance until a
 * real map SDK marker/drag interaction is wired in (see hooks/use-map.ts). */
export function MapLocationPicker({ onSelect }: MapLocationPickerProps) {
  const { isReady } = useMap();
  const { locate, isLocating, error } = useGeolocation();
  const [resolvedAddress, setResolvedAddress] = useState<string | null>(null);

  async function handleUseCurrentLocation() {
    const coords = await locate();
    if (!coords) return;
    const result = await reverseGeocode(coords.latitude, coords.longitude);
    setResolvedAddress(result.formatted_address);
    onSelect({
      latitude: coords.latitude,
      longitude: coords.longitude,
      formatted_address: result.formatted_address,
      city: result.city,
      state_region: result.state_region,
      country: result.country,
    });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-56 items-center justify-center rounded-card border border-line bg-muslin text-sm text-ink-soft">
        {isReady ? "Tap the map to drop a pin (map rendering pending SDK wiring)" : "Loading map…"}
      </div>
      <Button type="button" variant="secondary" onClick={handleUseCurrentLocation} isLoading={isLocating} className="self-start">
        Use my current location
      </Button>
      {resolvedAddress && <p className="text-sm text-ink-soft">{resolvedAddress}</p>}
      {error && <p className="text-sm text-thread">{error}</p>}
    </div>
  );
}

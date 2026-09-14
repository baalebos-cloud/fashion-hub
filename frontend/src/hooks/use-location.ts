import { useLocationStore } from "@/store/location.store";
import { locationsApi } from "@/api/locations.api";
import type { LocationType } from "@/types/location";

export function useLocation() {
  const { selectedLocation, setSelectedLocation } = useLocationStore();

  async function saveLocation(payload: {
    latitude: number;
    longitude: number;
    locationType: LocationType;
    formattedAddress?: string;
  }) {
    const saved = await locationsApi.create(payload);
    setSelectedLocation(saved);
    return saved;
  }

  return { selectedLocation, setSelectedLocation, saveLocation };
}

import { create } from "zustand";
import type { GeoLocation } from "@/types/location";

interface LocationState {
  selectedLocation: GeoLocation | null;
  setSelectedLocation: (location: GeoLocation | null) => void;
}

/** Holds the in-progress location a person is selecting on a map picker
 * (MapLocationPicker) before it's saved as an Address via locations.api.ts —
 * purely transient UI state, not persisted. */
export const useLocationStore = create<LocationState>((set) => ({
  selectedLocation: null,
  setSelectedLocation: (location) => set({ selectedLocation: location }),
}));

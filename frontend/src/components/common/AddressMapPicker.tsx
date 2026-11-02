import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import type { GeoLocation } from "@/types/location";

export type AddressSelection = Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">;

export function AddressMapPicker({ label, onAddressSelect }: {
  label: string;
  onAddressSelect: (location: AddressSelection) => void;
}) {
  return (
    <section aria-label={label}>
      <MapLocationPicker mode="delivery" onChange={onAddressSelect} onSelect={onAddressSelect} />
    </section>
  );
}

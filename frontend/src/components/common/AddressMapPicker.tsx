import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import type { PickedLocation } from "@/types/location";

export type AddressSelection = PickedLocation;

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

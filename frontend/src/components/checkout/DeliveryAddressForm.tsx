import { useId, useState, type FormEvent } from "react";
import { MapLocationPicker } from "./MapLocationPicker";
import type { GeoLocation } from "@/types/location";
import { addressesApi } from "@/api/addresses.api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { AddressInput, SavedAddress } from "@/types/address";

const addressFields = [
  ["label", "Address label", "text", 64],
  ["recipient_name", "Recipient name", "text", 255],
  ["recipient_phone", "Recipient phone", "tel", 32],
  ["formatted_address", "Street address", "text", 512],
  ["city", "City", "text", 128],
  ["state_region", "State or region", "text", 128],
  ["country", "Country code (two uppercase letters)", "text", 2],
] as const;

export function DeliveryAddressForm({ onSaved, initial, onSubmitAddress }: { onSaved: (address: SavedAddress) => void; initial?: SavedAddress; onSubmitAddress?: (payload: AddressInput) => Promise<SavedAddress> }) {
  const id = useId();
  const [values, setValues] = useState<AddressInput>(() => initial ? ({ label: initial.label, recipient_name: initial.recipient_name, recipient_phone: initial.recipient_phone, formatted_address: initial.formatted_address, city: initial.city, state_region: initial.state_region, country: initial.country, postal_code: initial.postal_code, latitude: initial.latitude, longitude: initial.longitude }) : ({ label: "Home", recipient_name: "", recipient_phone: "", formatted_address: "", city: "", state_region: "", country: "NG", latitude: Number.NaN, longitude: Number.NaN }));
  const [isResolving, setIsResolving] = useState(false);
  const hasPin = Number.isFinite(values.latitude) && Number.isFinite(values.longitude);
  function applyLocation(location: Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">) {
    setValues((old) => ({ ...old, latitude: location.latitude, longitude: location.longitude,
      formatted_address: location.formatted_address && !location.formatted_address.startsWith("Pinned location (") ? location.formatted_address : "",
      city: location.city || "", state_region: location.state_region || "",
      country: location.country?.toUpperCase() === "NIGERIA" ? "NG" : old.country,
    }));
  }
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!hasPin) { setError("Select a delivery pin on the map first."); return; }
    if (values.recipient_name.trim().length < 2 || !/^(?:\+234[789][01]\d{8}|0[789][01]\d{8})$/.test(values.recipient_phone.replace(/[\s()-]/g, ""))) {
      setError("Enter a recipient name (at least 2 characters) and a valid Nigerian phone number."); return;
    }
    setIsSaving(true);
    setError(null);
    try {
      onSaved(await (onSubmitAddress ?? addressesApi.create)(values));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }
  return (
    <form onSubmit={save} className="flex flex-col gap-3 rounded border border-sand p-4">
      <div><p className="mb-2 text-sm font-medium text-ink">Select your delivery point</p>
        <MapLocationPicker mode="delivery" onChange={applyLocation} onSelect={applyLocation} onResolvingChange={setIsResolving} />
        <p className="mt-2 text-xs text-ink-soft" role="status">{hasPin ? `Pin: ${values.latitude.toFixed(5)}, ${values.longitude.toFixed(5)}` : "A map pin is required to save this address."}</p>
      </div>
      {addressFields.map(([key, label, type, max]) => (
        <div key={key}>
          <label htmlFor={`${id}-${key}`} className="mb-1 block text-xs text-ink-soft">{label}</label>
          <Input id={`${id}-${key}`} type={type} value={values[key]} required maxLength={max}
            onChange={(e) => setValues((previous) => ({ ...previous, [key]: e.target.value }))} />
        </div>
      ))}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <Button type="submit" isLoading={isSaving} disabled={!hasPin || isResolving || isSaving}>Save delivery address</Button>
    </form>
  );
}

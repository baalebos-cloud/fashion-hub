import { useId, useState, type FormEvent } from "react";
import { MapLocationPicker } from "./MapLocationPicker";
import type { GeoLocation } from "@/types/location";
import { addressesApi } from "@/api/addresses.api";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { NIGERIA_LGAS, NIGERIA_STATES, matchLga, matchState } from "@/lib/locations/nigeria";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { AddressInput, SavedAddress } from "@/types/address";

const addressFields = [
  ["label", "Address label", "text", 64],
  ["recipient_name", "Recipient name", "text", 255],
  ["recipient_phone", "Recipient phone", "tel", 32],
  ["formatted_address", "Street address", "text", 512],
  ["city", "City or town", "text", 128],
] as const;

// Optional details riders use to find the door (LGA, landmark, nearest bus stop).
const localFields = [
  ["landmark", "Landmark", 255, "e.g. Opposite the blue mosque"],
  ["nearest_bus_stop", "Nearest bus stop", 255, "e.g. Jakande bus stop"],
  ["delivery_instructions", "Delivery instructions", 500, "e.g. Call at the gate"],
] as const;

export function DeliveryAddressForm({ onSaved, initial, onSubmitAddress }: { onSaved: (address: SavedAddress) => void; initial?: SavedAddress; onSubmitAddress?: (payload: AddressInput) => Promise<SavedAddress> }) {
  const id = useId();
  const [values, setValues] = useState<AddressInput>(() => initial ? ({ label: initial.label, recipient_name: initial.recipient_name, recipient_phone: initial.recipient_phone, formatted_address: initial.formatted_address, city: initial.city, state_region: matchState(initial.state_region) ?? initial.state_region, country: initial.country, postal_code: initial.postal_code, lga: matchLga(matchState(initial.state_region), initial.lga) ?? initial.lga, landmark: initial.landmark, nearest_bus_stop: initial.nearest_bus_stop, delivery_instructions: initial.delivery_instructions, latitude: initial.latitude, longitude: initial.longitude }) : ({ label: "Home", recipient_name: "", recipient_phone: "", formatted_address: "", city: "", state_region: "", country: "NG", latitude: Number.NaN, longitude: Number.NaN }));
  const [isResolving, setIsResolving] = useState(false);
  const inNigeria = (values.country || "NG").toUpperCase() === "NG";
  const stateKnown = Boolean(values.state_region && NIGERIA_LGAS[values.state_region]);
  const lgaOptions = stateKnown ? NIGERIA_LGAS[values.state_region] : [];
  function chooseState(state: string) {
    // A new state clears an LGA that doesn't belong to it.
    setValues((old) => ({ ...old, state_region: state, lga: matchLga(state, old.lga) ?? "" }));
  }
  const hasPin = Number.isFinite(values.latitude) && Number.isFinite(values.longitude);
  function applyLocation(location: Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">) {
    setValues((old) => ({ ...old, latitude: location.latitude, longitude: location.longitude,
      formatted_address: location.formatted_address ?? "",
      city: location.city || "",
      // The map says e.g. "Lagos State" or "Federal Capital Territory": use the listed state, and the
      // LGA when the map's area name is one of that state's LGAs; otherwise keep what was chosen.
      ...(() => {
        const state = matchState(location.state_region);
        if (!state) return { state_region: location.state_region || old.state_region };
        return { state_region: state, lga: matchLga(state, location.city) ?? matchLga(state, old.lga) ?? "" };
      })(),
      country: ["NIGERIA", "NG"].includes((location.country ?? "").toUpperCase()) ? "NG" : old.country,
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
    if (inNigeria && !stateKnown) { setError("Choose your state."); return; }
    if (inNigeria && !values.lga) { setError("Choose your local government area (LGA)."); return; }
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
      {inNigeria ? (
        <>
          <div>
            <label htmlFor={`${id}-state`} className="mb-1 block text-xs text-ink-soft">State</label>
            <Select id={`${id}-state`} required value={stateKnown ? values.state_region : ""}
              onChange={(e) => chooseState(e.target.value)}>
              <option value="" disabled>{values.state_region && !stateKnown ? `Choose (map said “${values.state_region}”)` : "Choose your state"}</option>
              {NIGERIA_STATES.map((state) => <option key={state} value={state}>{state === "FCT" ? "FCT (Abuja)" : state}</option>)}
            </Select>
          </div>
          <div>
            <label htmlFor={`${id}-lga`} className="mb-1 block text-xs text-ink-soft">Local government area (LGA)</label>
            <Select id={`${id}-lga`} required disabled={!stateKnown} value={lgaOptions.includes(values.lga ?? "") ? values.lga ?? "" : ""}
              onChange={(e) => setValues((old) => ({ ...old, lga: e.target.value }))}>
              <option value="" disabled>{stateKnown ? `Choose from ${lgaOptions.length} LGAs in ${values.state_region === "FCT" ? "the FCT" : values.state_region}` : "Choose your state first"}</option>
              {lgaOptions.map((lga) => <option key={lga} value={lga}>{lga}</option>)}
            </Select>
            {values.lga && stateKnown && !lgaOptions.includes(values.lga) && (
              <p className="mt-1 text-xs text-thread">“{values.lga}” isn't an LGA in {values.state_region}. Choose the right one.</p>
            )}
          </div>
        </>
      ) : (
        <div>
          <label htmlFor={`${id}-state_region`} className="mb-1 block text-xs text-ink-soft">State or region</label>
          <Input id={`${id}-state_region`} value={values.state_region} required maxLength={128}
            onChange={(e) => setValues((previous) => ({ ...previous, state_region: e.target.value }))} />
        </div>
      )}
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-xs font-medium text-ink">Help your rider find you (optional)</legend>
        {localFields.map(([key, label, max, hint]) => (
          <div key={key}>
            <label htmlFor={`${id}-${key}`} className="mb-1 block text-xs text-ink-soft">{label}</label>
            <Input id={`${id}-${key}`} type="text" value={values[key] ?? ""} maxLength={max} placeholder={hint}
              onChange={(e) => setValues((previous) => ({ ...previous, [key]: e.target.value }))} />
          </div>
        ))}
      </fieldset>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <Button type="submit" isLoading={isSaving} disabled={!hasPin || isResolving || isSaving}>Save delivery address</Button>
    </form>
  );
}

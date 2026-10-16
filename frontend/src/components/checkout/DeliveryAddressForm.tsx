import { useId, useState, type FormEvent } from "react";
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

export function DeliveryAddressForm({ onSaved }: { onSaved: (address: SavedAddress) => void }) {
  const id = useId();
  const [values, setValues] = useState<AddressInput>({ label: "Home", recipient_name: "", recipient_phone: "", formatted_address: "", city: "", state_region: "", country: "NG" });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      onSaved(await addressesApi.create(values));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }
  return (
    <form onSubmit={save} className="flex flex-col gap-3 rounded border border-sand p-4">
      {addressFields.map(([key, label, type, max]) => (
        <div key={key}>
          <label htmlFor={`${id}-${key}`} className="mb-1 block text-xs text-ink-soft">{label}</label>
          <Input id={`${id}-${key}`} type={type} value={values[key]} required maxLength={max}
            onChange={(e) => setValues((previous) => ({ ...previous, [key]: e.target.value }))} />
        </div>
      ))}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <Button type="submit" isLoading={isSaving}>Save delivery address</Button>
    </form>
  );
}

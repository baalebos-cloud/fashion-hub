import { useEffect, useState } from "react";
import { addressesApi } from "@/api/addresses.api";
import { DeliveryAddressForm } from "@/components/checkout/DeliveryAddressForm";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { SavedAddress } from "@/types/address";

export default function Addresses() {
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(null);
    addressesApi.list()
      .then((data) => { if (active) setAddresses(data); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [attempt]);
  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Delivery addresses</h1>
      <Button onClick={() => setIsAdding(!isAdding)}>{isAdding ? "Close address form" : "Add an address"}</Button>
      {isAdding && <DeliveryAddressForm onSaved={(address) => { setAddresses((previous) => [address, ...previous]); setIsAdding(false); }} />}
      {isLoading && <p role="status">Loading addresses…</p>}
      {error && <div><p role="alert" className="text-thread">{error}</p><Button onClick={() => setAttempt((value) => value + 1)}>Try again</Button></div>}
      {!isLoading && !error && addresses.length === 0 && <p className="text-sm text-ink-soft">Save a delivery address to use at checkout.</p>}
      <ul className="flex flex-col gap-3">{addresses.map((address) => <li key={address.id} className="rounded border border-line p-4">
        <h2 className="font-medium">{address.label}</h2>
        <p>{address.recipient_name} · {address.recipient_phone}</p>
        <p>{address.formatted_address}, {address.city}, {address.state_region}, {address.country}</p>
      </li>)}</ul>
    </div>
  );
}

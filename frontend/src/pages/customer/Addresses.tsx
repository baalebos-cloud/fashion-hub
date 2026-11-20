import { useEffect, useState } from "react";
import { addressesApi } from "@/api/addresses.api";
import { DeliveryAddressForm } from "@/components/checkout/DeliveryAddressForm";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { SavedAddress } from "@/types/address";

export default function Addresses() {
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [editing, setEditing] = useState<SavedAddress | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  async function makeDefault(id: string) {
    try { const updated = await addressesApi.setDefault(id); setAddresses((items) => items.map((a) => ({ ...a, is_default: a.id === updated.id }))); }
    catch (err) { setMutationError(getDisplayErrorMessage(err)); }
  }
  async function remove(id: string) {
    try { await addressesApi.remove(id); setAddresses((items) => items.filter((a) => a.id !== id)); }
    catch (err) { setMutationError(getDisplayErrorMessage(err)); }
  }
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
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-xl text-ink">Delivery addresses</h1>
          <p className="mt-1 text-sm text-ink-soft">Where riders bring your orders. Pin the exact spot so they find the door.</p>
        </div>
        {!editing && <Button variant={isAdding ? "secondary" : "primary"} onClick={() => setIsAdding(!isAdding)}>{isAdding ? "Close address form" : "Add an address"}</Button>}
      </div>
      {(isAdding || editing) && (
        <section aria-label={editing ? "Edit address" : "New address"} className="flex flex-col gap-2">
          {editing && (
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium text-ink">Editing “{editing.label}”</h2>
              <button type="button" onClick={() => setEditing(null)} className="text-sm text-ink-soft underline">Cancel</button>
            </div>
          )}
          <DeliveryAddressForm key={editing?.id ?? "new"} initial={editing ?? undefined}
            onSubmitAddress={editing ? (payload) => addressesApi.update(editing.id, payload) : undefined}
            onSaved={(address) => { setAddresses((previous) => editing ? previous.map((a) => a.id === address.id ? address : a) : [address, ...previous]); setIsAdding(false); setEditing(null); }} />
        </section>
      )}
      {mutationError && <p role="alert" className="text-sm text-thread">{mutationError}</p>}
      {isLoading && <p role="status">Loading addresses…</p>}
      {error && <div className="flex flex-col items-start gap-2"><p role="alert" className="text-sm text-thread">{error}</p><Button onClick={() => setAttempt((value) => value + 1)}>Try again</Button></div>}
      {!isLoading && !error && addresses.length === 0 && !isAdding && (
        <div className="rounded-card border border-dashed border-line-strong bg-surface p-5 text-sm text-ink-soft">
          No saved addresses yet. Add one to use at checkout.
        </div>
      )}
      <ul className="flex flex-col gap-3">{addresses.map((address) => <li key={address.id}>
        <Card className="flex flex-col gap-1 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-medium text-ink">{address.label}</h2>
            {address.is_default && <Badge tone="success">Default</Badge>}
          </div>
          <p className="text-sm text-ink">{address.recipient_name} · {address.recipient_phone}</p>
          <p className="text-sm text-ink-soft">{[address.formatted_address, address.city, address.lga, address.state_region, address.country?.toUpperCase() === "NG" ? null : address.country].filter(Boolean).join(", ")}</p>
          <div className="mt-2 flex flex-wrap gap-4 text-sm">
            {!address.is_default && <button type="button" onClick={() => void makeDefault(address.id)} className="text-brass-deep underline">Set default</button>}
            <button type="button" onClick={() => { setEditing(address); setIsAdding(false); }} className="text-brass-deep underline">Edit</button>
            <button type="button" onClick={() => void remove(address.id)} className="text-thread underline">Delete</button>
          </div>
        </Card>
      </li>)}</ul>
    </div>
  );
}

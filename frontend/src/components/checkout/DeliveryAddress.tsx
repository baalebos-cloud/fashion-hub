import { useState } from "react";
import { cn } from "@/lib/utils/cn";
import { MapLocationPicker } from "./MapLocationPicker";
import { Button } from "@/components/ui/button";
import type { Address } from "@/types/location";

export function DeliveryAddress({ addresses, selectedId, onSelect, onAddNew }: { addresses: Address[]; selectedId: string | null; onSelect: (id: string) => void; onAddNew: () => void }) {
  const [isAdding, setIsAdding] = useState(false);

  return (
    <div className="flex flex-col gap-3">
      {addresses.map((address) => (
        <button
          key={address.id}
          onClick={() => onSelect(address.id)}
          className={cn(
            "rounded-card border p-3 text-left text-sm",
            selectedId === address.id ? "border-brass bg-muslin" : "border-line hover:border-brass"
          )}
        >
          <div className="font-medium text-ink">{address.label ?? "Address"}</div>
          {address.recipient_name && <div className="text-ink-soft">{address.recipient_name}</div>}
        </button>
      ))}

      {!isAdding && (
        <Button type="button" variant="secondary" onClick={() => setIsAdding(true)} className="self-start">
          Add a new address
        </Button>
      )}
      {isAdding && (
        <MapLocationPicker
          onSelect={() => {
            onAddNew();
            setIsAdding(false);
          }}
        />
      )}
    </div>
  );
}

import { useState } from "react";
import { DeliveryAddress } from "@/components/checkout/DeliveryAddress";
import type { Address } from "@/types/location";

export default function Addresses() {
  const [addresses] = useState<Address[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="max-w-md">
      <h1 className="mb-6 font-display text-xl text-ink">Addresses</h1>
      <DeliveryAddress addresses={addresses} selectedId={selectedId} onSelect={setSelectedId} onAddNew={() => {}} />
    </div>
  );
}

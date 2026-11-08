import { useEffect, useState } from "react";
import { callsApi } from "@/api/calls.api";
import { Card } from "@/components/ui/card";
import { CallButton } from "./CallButton";
import type { CallContact, CallParty } from "@/types/call";

const PARTY_ROLE: Record<CallParty, string> = { buyer: "Customer", seller: "Seller", rider: "Rider" };

/** "Contact" panel for an order: masked call buttons for everyone the user may call.
 * `refreshKey` reloads the list when it changes, e.g. once a rider is assigned. */
export function OrderContacts({ orderId, refreshKey }: { orderId: string; refreshKey?: string }) {
  const [contacts, setContacts] = useState<CallContact[] | null>(null);

  useEffect(() => {
    let active = true;
    callsApi.contacts(orderId).then((list) => { if (active) setContacts(list); }).catch(() => { if (active) setContacts([]); });
    return () => { active = false; };
  }, [orderId, refreshKey]);

  if (!contacts || contacts.length === 0) return null;

  return (
    <Card role="region" className="flex flex-col gap-3" aria-label="Contact about this order">
      <div>
        <h2 className="text-sm font-medium text-ink">Contact about this order</h2>
        <p className="text-xs text-ink-soft">Calls go through Tailora, so phone numbers stay private on both sides.</p>
      </div>
      <ul className="flex flex-col gap-3">
        {contacts.map((contact) => (
          <li key={contact.party} className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium text-ink">{contact.display_name}</p>
              <p className="text-xs text-ink-soft">{contact.available ? PARTY_ROLE[contact.party] : contact.reason}</p>
            </div>
            <CallButton orderId={orderId} party={contact.party} label="Call" disabled={!contact.available} />
          </li>
        ))}
      </ul>
    </Card>
  );
}

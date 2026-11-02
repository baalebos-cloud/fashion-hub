import { useEffect, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery } from "@/types/delivery";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";

export function CustomerDeliveryTracking({ orderId }: { orderId: string }) {
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [handoverCode, setHandoverCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const next = await deliveriesApi.getByOrder(orderId);
        if (active) {
          setDelivery(next);
          if (next?.status !== "in_transit") setHandoverCode(null);
        }
      } catch {
        if (active) setError("Delivery tracking is temporarily unavailable.");
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 20000);
    return () => { active = false; window.clearInterval(timer); };
  }, [orderId]);

  async function showCode() {
    if (!delivery) return;
    setError(null);
    try {
      setHandoverCode(await deliveriesApi.getHandoverCode(delivery.id));
    } catch {
      setError("The handover code is unavailable. Check that your courier has picked up the package.");
    }
  }

  return (
    <section className="space-y-2 rounded-card border border-line p-4" aria-label="Delivery tracking">
      <h2 className="font-medium">Delivery tracking</h2>
      {delivery ? <DeliveryStatusBadge status={delivery.status} /> :
        <p className="text-sm text-ink-soft">No courier has been assigned yet.</p>}
      {delivery?.status === "in_transit" && (
        <button type="button" onClick={() => void showCode()} className="rounded border border-line p-2 text-sm">
          Show handover code
        </button>
      )}
      {handoverCode && <p role="status" className="text-sm">
        Share this code with your assigned rider only when you receive your package:
        <strong className="ml-2 tracking-widest">{handoverCode}</strong>
      </p>}
      <p className="text-xs text-ink-soft">Delivery stage refreshes every 20 seconds. Live rider GPS and arrival times are not yet available.</p>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </section>
  );
}

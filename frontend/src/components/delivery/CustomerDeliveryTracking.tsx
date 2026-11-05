import { useEffect, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery, RiderPosition } from "@/types/delivery";
import { DeliveryMap } from "./DeliveryMap";
import { CallButton } from "@/components/calls/CallButton";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { RiderCard } from "@/components/delivery/RiderCard";
import { OneTimeCode } from "@/components/delivery/OneTimeCode";

export function CustomerDeliveryTracking({ orderId }: { orderId: string }) {
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [riderPosition, setRiderPosition] = useState<RiderPosition | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const next = await deliveriesApi.getByOrder(orderId);
        if (active) {
          setDelivery(next);
          if (next?.status !== "in_transit") { setShowCode(false); setRiderPosition(null); }
        }
        if (next?.status === "in_transit") {
          const position = await deliveriesApi.getPosition(next.id).catch(() => null);
          if (active) setRiderPosition(position);
        }
      } catch {
        if (active) { setRiderPosition(null); setError("Delivery tracking is temporarily unavailable."); }
      }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 20000);
    return () => { active = false; window.clearInterval(timer); };
  }, [orderId]);

  return (
    <section className="space-y-2 rounded-card border border-line p-4" aria-label="Delivery tracking">
      <h2 className="font-medium">Delivery tracking</h2>
      {delivery ? <DeliveryStatusBadge status={delivery.status} /> :
        <p className="text-sm text-ink-soft">No courier has been assigned yet.</p>}
      {delivery?.rider_name && <RiderCard delivery={delivery} />}
      {delivery?.rider_name && ["assigned", "picked_up", "in_transit", "out_for_delivery"].includes(delivery.status) && (
        <CallButton orderId={orderId} party="rider" label="Call rider" />
      )}
      {delivery?.status === "in_transit" && delivery.package_count != null && (
        <p className="text-sm text-ink-soft">
          Your rider collected {delivery.package_count} package{delivery.package_count === 1 ? "" : "s"}. Check they're all there.
        </p>
      )}
      {delivery?.status === "in_transit" && !showCode && (
        <button type="button" onClick={() => setShowCode(true)} className="rounded border border-line p-2 text-sm">
          Show handover code
        </button>
      )}
      {delivery?.status === "in_transit" && showCode && (
        <OneTimeCode
          key={delivery.id}
          label="Handover code"
          hint="Give this code to your rider only after you have the package in hand."
          load={async () => { const c = await deliveriesApi.getHandoverCode(delivery.id); return { code: c.handover_code, expiresAt: c.expires_at }; }}
          rotate={async () => { const c = await deliveriesApi.rotateHandoverCode(delivery.id); return { code: c.handover_code, expiresAt: c.expires_at }; }}
        />
      )}
      {delivery?.status === "in_transit" && riderPosition && (
        <div className="space-y-2">
          <p className="text-xs text-ink-soft">
            Rider-reported GPS, accuracy ±{Math.round(riderPosition.accuracy_m)} m,
            updated {new Date(riderPosition.recorded_at).toLocaleTimeString()}.
          </p>
          <DeliveryMap currentLat={riderPosition.latitude} currentLng={riderPosition.longitude} />
        </div>
      )}
      {delivery?.status === "in_transit" && !riderPosition && (
        <p className="text-sm text-ink-soft">Your rider is not currently sharing their location.</p>
      )}
      <p className="text-xs text-ink-soft">Delivery stages and shared GPS refresh every 20 seconds. Arrival times are not estimated.</p>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </section>
  );
}

import { useEffect, useRef, useState } from "react";
import { describeFreshness } from "@/lib/utils/tracking";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery, RiderPosition } from "@/types/delivery";
import { DeliveryMap } from "./DeliveryMap";
import { Button } from "@/components/ui/button";
import { DeliveryStatusBadge } from "@/components/delivery/DeliveryStatusBadge";
import { RiderCard } from "@/components/delivery/RiderCard";
import { OneTimeCode } from "@/components/delivery/OneTimeCode";

export function CustomerDeliveryTracking({ orderId }: { orderId: string }) {
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [riderPosition, setRiderPosition] = useState<RiderPosition | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nextDelay = useRef(20000);
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
          nextDelay.current = position?.freshness === "live" ? 10000 : 20000;
        }
      } catch {
        if (active) { setRiderPosition(null); setError("Delivery tracking is temporarily unavailable."); }
      }
    }
    // Poll faster while the rider is sharing live; slower otherwise (and pause in background tabs).
    let timer: number | undefined;
    const schedule = (ms: number) => { timer = window.setTimeout(async () => { await refresh(); schedule(nextDelay.current); }, ms); };
    void refresh().then(() => schedule(nextDelay.current));
    return () => { active = false; if (timer) window.clearTimeout(timer); };
  }, [orderId]);

  return (
    <section className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5" aria-label="Delivery tracking">
      <h2 className="font-semibold text-ink">Delivery tracking</h2>
      {delivery ? <DeliveryStatusBadge status={delivery.status} /> :
        <p className="text-sm text-ink-soft">No courier has been assigned yet.</p>}
      {delivery?.courier && <p className="text-sm text-ink">Delivered by our courier partner <span className="font-medium">{delivery.courier}</span>.</p>}
      {delivery?.rider_name && <RiderCard delivery={delivery} />}
      {/* Calling the rider lives in "Contacts" on the order page, which knows whether masked calls are set up. */}
      {delivery?.status === "in_transit" && delivery.package_count != null && (
        <p className="text-sm text-ink-soft">
          Your rider collected {delivery.package_count} package{delivery.package_count === 1 ? "" : "s"}. Check they're all there.
        </p>
      )}
      {delivery?.status === "in_transit" && !showCode && (
        <Button type="button" variant="secondary" size="sm" className="self-start" onClick={() => setShowCode(true)}>
          Show handover code
        </Button>
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
      {delivery?.status === "in_transit" && riderPosition && (() => {
        const fresh = describeFreshness(riderPosition.freshness ?? "live", riderPosition.age_seconds);
        return (
          <div className="space-y-2">
            <p className={`text-xs ${fresh.current ? "text-ink-soft" : "font-medium text-thread"}`} data-testid="rider-freshness">
              {fresh.label}. Rider-reported GPS, accuracy ±{Math.round(riderPosition.accuracy_m)} m.
            </p>
            <div className={fresh.current ? "" : "opacity-60"}>
              <DeliveryMap currentLat={riderPosition.latitude} currentLng={riderPosition.longitude} />
            </div>
          </div>
        );
      })()}
      {delivery?.status === "in_transit" && !riderPosition && (
        <p className="text-sm text-ink-soft">Your rider is not currently sharing their location.</p>
      )}
      <p className="text-xs text-ink-soft">Updates every 10 seconds while the rider shares live, otherwise every 20 seconds.</p>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </section>
  );
}

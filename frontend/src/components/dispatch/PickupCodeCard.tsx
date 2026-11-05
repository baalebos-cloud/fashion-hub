import { useEffect, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { OneTimeCode } from "@/components/delivery/OneTimeCode";
import { Card } from "@/components/ui/card";
import type { Delivery } from "@/types/delivery";

const REFRESH_MS = 20_000;

/**
 * Seller-side: while an assigned rider is on the way to collect, show the pickup code the
 * rider must enter. Only the seller sees it; it disappears once the package is collected.
 */
export function PickupCodeCard({ orderId }: { orderId: string }) {
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [required, setRequired] = useState(true);

  useEffect(() => {
    let active = true;
    const refresh = () => deliveriesApi.getByOrder(orderId)
      .then((next) => { if (active) setDelivery(next); })
      .catch(() => undefined);
    void refresh();
    const timer = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => { active = false; window.clearInterval(timer); };
  }, [orderId]);

  if (!delivery || delivery.status !== "assigned" || !required) return null;

  const toView = (code: Awaited<ReturnType<typeof deliveriesApi.getPickupCode>>) => {
    if (!code.required || !code.pickup_code || !code.expires_at) {
      setRequired(false);
      throw new Error("not required");
    }
    return { code: code.pickup_code, expiresAt: code.expires_at };
  };

  return (
    <Card className="flex flex-col gap-2 p-4">
      <h2 className="text-sm font-medium text-ink">Hand over to {delivery.rider_name ?? "the rider"}</h2>
      <OneTimeCode
        key={delivery.id}
        label="Pickup code"
        hint="Give this code to the rider only when they collect the package in person. Never share it by phone or chat."
        load={async () => toView(await deliveriesApi.getPickupCode(delivery.id))}
        rotate={async () => toView(await deliveriesApi.rotatePickupCode(delivery.id))}
      />
    </Card>
  );
}

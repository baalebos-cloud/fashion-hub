import { useParams, useNavigate } from "react-router-dom";
import { useDelivery } from "@/hooks/use-delivery";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { deliveryRoutes } from "@/config/routes.config";
import { useState } from "react";

/** Requires a `POST /deliveries/{id}/picked-up` endpoint, which isn't in
 * the current backend scaffold (only `DeliveryService.mark_picked_up`
 * exists as a Python method — see backend/app/services/delivery_service.py
 * — with no route wired to it yet in backend/app/api/v1/deliveries.py).
 * Wire the real call in once that route exists. */
export default function Pickup() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading } = useDelivery(deliveryId);
  const navigate = useNavigate();
  const [isConfirming, setIsConfirming] = useState(false);

  if (isLoading || !delivery) return <LoadingScreen />;

  async function handleConfirm() {
    if (!deliveryId) return;
    setIsConfirming(true);
    try {
      navigate(deliveryRoutes.navigation(deliveryId));
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="max-w-sm">
      <h1 className="mb-4 font-display text-xl text-ink">Confirm pickup</h1>
      <Button onClick={handleConfirm} isLoading={isConfirming}>I've picked up the package</Button>
    </div>
  );
}

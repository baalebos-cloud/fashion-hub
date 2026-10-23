import { useParams, useNavigate } from "react-router-dom";
import { useDelivery } from "@/hooks/use-delivery";
import { deliveriesApi } from "@/api/deliveries.api";
import { Button } from "@/components/ui/button";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { deliveryRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useState } from "react";

export default function Pickup() {
  const { deliveryId } = useParams<{ deliveryId: string }>();
  const { delivery, isLoading, error } = useDelivery(deliveryId);
  const navigate = useNavigate();
  const [isConfirming, setIsConfirming] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (error) return <p role="alert" className="text-thread">{error}</p>;
  if (isLoading || !delivery) return <LoadingScreen label="Loading delivery…" />;

  async function handleConfirm() {
    if (!deliveryId) return;
    setActionError(null);
    setIsConfirming(true);
    try {
      await deliveriesApi.markPickedUp(deliveryId);
      navigate(deliveryRoutes.navigation(deliveryId));
    } catch (err) {
      setActionError(getDisplayErrorMessage(err));
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="max-w-sm">
      <h1 className="mb-4 font-display text-xl text-ink">Confirm pickup</h1>
      <Button onClick={() => void handleConfirm()} isLoading={isConfirming}>I've picked up the package</Button>
      {actionError && <p role="alert" className="mt-3 text-sm text-thread">{actionError}</p>}
    </div>
  );
}

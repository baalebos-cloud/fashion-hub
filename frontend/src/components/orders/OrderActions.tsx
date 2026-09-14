import { Button } from "@/components/ui/button";
import { MarkReceivedButton } from "./MarkReceivedButton";
import { useAuth } from "@/hooks/use-auth";
import type { Order } from "@/types/order";

export interface OrderActionsProps {
  order: Order;
  onAccept: () => Promise<void>;
  onStartProduction: () => Promise<void>;
  onMarkReady: () => Promise<void>;
  onShip: () => Promise<void>;
  onMarkReceived: () => Promise<void>;
}

/**
 * Shows only the action(s) valid for the CURRENT status and the CURRENT
 * user's role — this narrows what's clickable, but the backend
 * independently re-validates both the transition and the actor's
 * ownership on every one of these calls regardless (see
 * backend/app/services/order_service.py). Never assume "the button was
 * shown" implies "the action will succeed."
 */
export function OrderActions({ order, onAccept, onStartProduction, onMarkReady, onShip, onMarkReceived }: OrderActionsProps) {
  const { user } = useAuth();
  const isProfessional = user?.role === "tailor" || user?.role === "designer";

  return (
    <div className="flex flex-wrap gap-2">
      {isProfessional && order.status === "paid" && <Button onClick={onAccept}>Accept order</Button>}
      {isProfessional && order.status === "accepted" && <Button onClick={onStartProduction}>Start production</Button>}
      {isProfessional && order.status === "in_production" && <Button onClick={onMarkReady}>Mark ready</Button>}
      {isProfessional && order.status === "ready_for_delivery" && <Button onClick={onShip}>Ship order</Button>}
      <MarkReceivedButton order={order} onConfirm={onMarkReceived} />
    </div>
  );
}

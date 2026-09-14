import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "react-router-dom";
import { professionalRoutes } from "@/config/routes.config";

export default function Delivery() {
  const { orders } = useOrders();
  const inTransit = orders.filter((o) => ["shipped", "out_for_delivery", "picked_up", "in_transit"].includes(o.status));

  if (inTransit.length === 0) {
    return <EmptyState title="No deliveries in progress" />;
  }

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Delivery</h1>
      <div className="flex flex-col gap-3">
        {inTransit.map((order) => (
          <Link key={order.id} to={professionalRoutes.trackDelivery(order.id)}>
            <Card className="transition-colors hover:border-brass">{order.order_number} — {order.status.replace(/_/g, " ")}</Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

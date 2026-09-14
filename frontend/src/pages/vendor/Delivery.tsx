import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "react-router-dom";
import { vendorRoutes } from "@/config/routes.config";

export default function Delivery() {
  const { orders } = useOrders();
  const outbound = orders.filter((o) => ["ready_for_pickup", "picked_up", "in_transit"].includes(o.status));

  if (outbound.length === 0) return <EmptyState title="No deliveries in progress" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Delivery</h1>
      <div className="flex flex-col gap-3">
        {outbound.map((order) => (
          <Link key={order.id} to={vendorRoutes.trackDelivery(order.id)}>
            <Card className="transition-colors hover:border-brass">{order.order_number} — {order.status.replace(/_/g, " ")}</Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

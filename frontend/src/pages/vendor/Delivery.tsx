import { useOrders } from "@/hooks/use-orders";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Link } from "react-router-dom";
import { vendorRoutes } from "@/config/routes.config";
import { VendorPickupLocation } from "@/components/dispatch/VendorPickupLocation";

export default function Delivery() {
  const { orders } = useOrders();
  const outbound = orders.filter((o) => ["ready_for_pickup", "picked_up", "in_transit"].includes(o.status));

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Delivery</h1>
      <VendorPickupLocation />
      {outbound.length === 0 && <EmptyState title="No deliveries in progress" description="Orders ready for pickup or on the way appear here." />}
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

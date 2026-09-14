import { useState } from "react";
import { Link } from "react-router-dom";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import { EmptyState } from "@/components/ui/empty-state";
import { deliveryRoutes } from "@/config/routes.config";
import type { Delivery } from "@/types/delivery";

export default function ActiveDeliveries() {
  const [deliveries] = useState<Delivery[]>([]);

  if (deliveries.length === 0) {
    return <EmptyState title="No active deliveries" description="Accept a request to see it here." />;
  }

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">Active deliveries</h1>
      {deliveries.map((delivery) => (
        <Link key={delivery.id} to={deliveryRoutes.details(delivery.id)}>
          <DeliveryCard delivery={delivery} detailsPath={deliveryRoutes.details(delivery.id)} />
        </Link>
      ))}
    </div>
  );
}

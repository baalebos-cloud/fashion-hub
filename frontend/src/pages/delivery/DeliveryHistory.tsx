import { useState } from "react";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import { EmptyState } from "@/components/ui/empty-state";
import { deliveryRoutes } from "@/config/routes.config";
import type { Delivery } from "@/types/delivery";

export default function DeliveryHistory() {
  const [deliveries] = useState<Delivery[]>([]);

  if (deliveries.length === 0) return <EmptyState title="No completed deliveries yet" />;

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">Delivery history</h1>
      {deliveries.map((delivery) => (
        <DeliveryCard key={delivery.id} delivery={delivery} detailsPath={deliveryRoutes.details(delivery.id)} />
      ))}
    </div>
  );
}

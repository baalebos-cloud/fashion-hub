import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api/client";
import { Link } from "react-router-dom";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import { EmptyState } from "@/components/ui/empty-state";
import { deliveryRoutes } from "@/config/routes.config";
import type { Delivery } from "@/types/delivery";

export default function ActiveDeliveries() {
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    apiClient.get<Delivery[]>("/deliveries/mine/active")
      .then(response => { if (active) setDeliveries(response.data); })
      .catch(() => { if (active) setError("Unable to load deliveries. Please retry."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  if (loading) return <p role="status">Loading active deliveries…</p>;
  if (error) return <p role="alert" className="text-thread">{error}</p>;

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

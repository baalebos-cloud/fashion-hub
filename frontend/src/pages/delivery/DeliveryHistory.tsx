import { useEffect, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { DeliveryCard } from "@/components/delivery/DeliveryCard";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { deliveryRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Delivery } from "@/types/delivery";

const PAGE_SIZE = 20;

/** Jobs the rider has finished (delivered, failed or cancelled), newest first. */
export default function DeliveryHistory() {
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    deliveriesApi.myHistory(page, PAGE_SIZE)
      .then((rows) => {
        if (!active) return;
        setDeliveries((old) => (page === 1 ? rows : [...old, ...rows]));
        setHasMore(rows.length === PAGE_SIZE);
        setError(null);
      })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Couldn't load your past deliveries.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page]);

  if (loading && deliveries.length === 0) return <p role="status">Loading your past deliveries…</p>;
  if (error && deliveries.length === 0) return <p role="alert" className="text-thread">{error}</p>;
  if (deliveries.length === 0) {
    return <EmptyState title="No completed deliveries yet" description="Jobs you deliver show up here, with the fare for each." />;
  }

  return (
    <div className="flex flex-col gap-3">
      <h1 className="font-display text-xl text-ink">Delivery history</h1>
      {deliveries.map((delivery) => (
        <DeliveryCard key={delivery.id} delivery={delivery} detailsPath={deliveryRoutes.details(delivery.id)} />
      ))}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {hasMore && (
        <Button variant="secondary" className="self-start" isLoading={loading} onClick={() => setPage((p) => p + 1)}>
          Show older deliveries
        </Button>
      )}
    </div>
  );
}

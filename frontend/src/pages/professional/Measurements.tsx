import { useOrders } from "@/hooks/use-orders";
import { EmptyState } from "@/components/ui/empty-state";

/** Read-only view of measurement profiles attached to this professional's
 * incoming orders. Requires the backend to expose the linked
 * MeasurementProfile on GET /orders/{id} (currently only
 * measurement_profile_id is implied, not embedded) — extend
 * types/order.ts + api/orders.api.ts once that's available. */
export default function Measurements() {
  const { orders } = useOrders();

  if (orders.length === 0) {
    return <EmptyState title="No measurements yet" description="Customer measurements will appear here once orders come in." />;
  }

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Customer measurements</h1>
      <p className="text-sm text-ink-soft">Open an individual order to view its measurement profile.</p>
    </div>
  );
}

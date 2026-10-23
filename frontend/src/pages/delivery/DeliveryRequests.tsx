import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deliveryRequestsApi, type InternalDeliveryRequest } from "@/api/delivery-requests.api";
import { deliveryRoutes } from "@/config/routes.config";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export default function DeliveryRequests() {
  const navigate = useNavigate();
  const [items, setItems] = useState<InternalDeliveryRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    deliveryRequestsApi.available().then((data) => {
      if (active) { setItems(data); setError(null); }
    }).catch((err: unknown) => {
      if (active) setError(getDisplayErrorMessage(err));
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [refreshKey]);

  async function claim(requestId: string) {
    setBusy(requestId);
    setError(null);
    try {
      const delivery = await deliveryRequestsApi.accept(requestId);
      navigate(deliveryRoutes.details(delivery.id));
    } catch (err) {
      setError(getDisplayErrorMessage(err));
      setRefreshKey((key) => key + 1);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="font-display text-xl text-ink">Delivery requests</h1>
        <Button variant="secondary" size="sm" onClick={() => setRefreshKey((key) => key + 1)}>Refresh</Button>
      </div>
      <p className="text-sm text-ink-soft">
        Available internal deliveries are shown here. Address details are shared only after assignment.
      </p>
      {loading && <p role="status">Checking available deliveries…</p>}
      {error && <p role="alert" className="text-thread">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <EmptyState title="No delivery requests right now" description="Refresh to look for new assignments." />
      )}
      {!loading && items.map((item) => (
        <div key={item.id} className="flex items-center justify-between gap-4 rounded-card border border-line p-4">
          <div className="text-sm text-ink">Order {item.order_id.slice(0, 8)}</div>
          <Button size="sm" disabled={busy !== null} isLoading={busy === item.id}
            onClick={() => void claim(item.id)}>Accept delivery</Button>
        </div>
      ))}
    </div>
  );
}

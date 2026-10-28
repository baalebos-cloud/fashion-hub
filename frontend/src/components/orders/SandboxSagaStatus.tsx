import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { orderKeys } from "@/api/query-keys";

interface SagaStatus {
  order_id: string;
  state: string;
  simulation: true;
  provider_funds_verified: false;
  receipt: null;
}

export function SandboxSagaStatus({ orderId }: { orderId: string }) {
  // Never show sandbox financial badges on the production customer UI.
  const enabled = import.meta.env.VITE_SAGA_SANDBOX_UI_ENABLED === "true" && Boolean(orderId);
  const query = useQuery({
    queryKey: [...orderKeys.detail(orderId), "saga"],
    queryFn: async () => {
      const { data } = await apiClient.get<SagaStatus>(`/saga/orders/${encodeURIComponent(orderId)}`);
      return data;
    },
    enabled,
    refetchInterval: (q) =>
      q.state.data?.state === "COMPLETED" ||
      q.state.data?.state === "CANCELLED_REFUNDED" ||
      q.state.data?.state === "REVIEW_REQUIRED" ? false : 10000,
    staleTime: 1000 * 60 * 5,
    retry: 1,
  });
  if (!enabled) return null;
  return (
    <section aria-live="polite" className="rounded-lg border border-line p-4">
      <h2 className="font-medium text-ink">Sandbox order orchestration</h2>
      <p className="text-sm text-ink-soft">Simulation only. No real funds held or refunded.</p>
      {query.isPending && <p role="status">Checking Saga status…</p>}
      {query.isError && <p role="alert">Saga status temporarily unavailable. Payment status has not changed.</p>}
      {query.data && (
        <>
          <p className="text-sm">Current step: {query.data.state.replaceAll("_", " ")}</p>
          {query.data.state === "COMPENSATING" && (
            <p role="status">Compensation requested. Await independent provider reconciliation.</p>
          )}
          {query.data.state === "CANCELLED_REFUNDED" && (
            <p role="status">Sandbox refund simulation recorded, not a real refund receipt.</p>
          )}
          {query.data.state === "REVIEW_REQUIRED" && (
            <p role="alert">Manual review required. No automatic refund is assumed.</p>
          )}
        </>
      )}
    </section>
  );
}

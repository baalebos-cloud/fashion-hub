import { useEffect, useState } from "react";
import { adminDispatchApi, type AdminDispatchBoard } from "@/api/admin-dispatch.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function Deliveries() {
  const [board, setBoard] = useState<AdminDispatchBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    adminDispatchApi.board().then((data) => {
      if (active) { setBoard(data); setError(null); }
    }).catch(() => {
      if (active) setError("Unable to load the dispatch board. Check administrator permissions.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [revision]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-display text-xl text-ink">Dispatch operations</h1>
        <Button variant="secondary" size="sm" disabled={loading}
          onClick={() => setRevision((current) => current + 1)}>Refresh</Button>
      </div>
      {loading && <p role="status" className="text-sm text-ink-soft">Loading dispatch board…</p>}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {board && !error && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Card><p className="text-xs text-ink-soft">Awaiting rider</p>
              <p className="text-2xl font-medium">{board.unassigned_count}</p></Card>
            <Card><p className="text-xs text-ink-soft">Active deliveries</p>
              <p className="text-2xl font-medium">{board.active_count}</p></Card>
            <Card><p className="text-xs text-ink-soft">Verified and available riders</p>
              <p className="text-2xl font-medium">{board.available_verified_riders}</p></Card>
          </div>
          <section className="space-y-3" aria-label="Unassigned delivery requests">
            <h2 className="font-display text-lg">Unassigned requests</h2>
            {board.pending.length === 0 && <p className="text-sm text-ink-soft">No requests awaiting assignment.</p>}
            {board.pending.map((request) => (
              <div key={request.id} className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line p-4 text-sm">
                <span>Order {request.order_id.slice(0, 8)}</span>
                <span className="text-ink-soft">{request.status.replaceAll("_", " ")}</span>
              </div>
            ))}
          </section>
          <section className="space-y-3" aria-label="Active delivery assignments">
            <h2 className="font-display text-lg">Active rider assignments</h2>
            {board.active.length === 0 && <p className="text-sm text-ink-soft">No active rider assignments.</p>}
            {board.active.map((run) => (
              <div key={run.id} className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line p-4 text-sm">
                <div>
                  <p>Order {run.order_id.slice(0, 8)}</p>
                  <p className="text-xs text-ink-soft">Courier {run.delivery_partner_id?.slice(0, 8) ?? "Not assigned"}
                    {run.vehicle_type ? ` · ${run.vehicle_type}` : ""}</p>
                </div>
                <span className="capitalize text-ink-soft">{run.status.replaceAll("_", " ")}</span>
              </div>
            ))}
          </section>
          <p className="text-xs text-ink-soft">
            Results are limited to the most recent 50 pending and 100 active deliveries.
            This read-only board does not change rider assignments or payment amounts.
          </p>
        </>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { adminDispatchApi, type AdminDispatchBoard, type AvailableRider, type DispatchIssue } from "@/api/admin-dispatch.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { DispatchAction } from "@/components/dispatch/DispatchAction";
import { DeliveryEventLog } from "@/components/dispatch/DeliveryEventLog";
import { RoutingHealth } from "@/components/admin/RoutingHealth";
import { SuggestedRiders } from "@/components/dispatch/SuggestedRiders";
import { RiderRouteToggle } from "@/components/dispatch/RiderRouteToggle";
import { ControlTower } from "@/components/dispatch/ControlTower";
import { describeFreshness } from "@/lib/utils/tracking";

const ISSUE_LABEL: Record<string, string> = {
  CUSTOMER_UNREACHABLE: "Customer unreachable", WRONG_ADDRESS: "Wrong address", PACKAGE_DAMAGED: "Package damaged",
  TRAFFIC_ACCIDENT_DELAY: "Traffic or accident delay", RECIPIENT_REJECTED: "Recipient rejected", VEHICLE_BREAKDOWN: "Vehicle breakdown",
};
const LEG: Record<string, string> = { customer_order: "Garment → customer", vendor_order: "Materials → tailor" };

function orderLabel(row: { order_number: string | null; order_id: string; order_type: string | null }) {
  return (
    <>
      <span className="font-medium text-ink">{row.order_number ?? `Order ${row.order_id.slice(0, 8)}`}</span>
      {row.order_type && <span className="ml-2 text-xs text-ink-soft">{LEG[row.order_type] ?? row.order_type}</span>}
    </>
  );
}

function ReassignPicker({ riders, value, onChange }: { riders: AvailableRider[]; value: string; onChange: (v: string) => void }) {
  if (riders.length === 0) return <p className="text-xs text-thread">No verified riders are online right now.</p>;
  return (
    <label className="text-xs text-ink-soft">
      New rider
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm text-ink focus:border-brass focus:outline-none">
        <option value="">Choose a rider…</option>
        {riders.map((r) => (
          <option key={r.id} value={r.id}>
            {r.first_name}{r.vehicle_type ? ` · ${r.vehicle_type}` : ""}{r.rating > 0 ? ` · ★ ${r.rating.toFixed(1)}` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

function ReassignAction({ deliveryId, riders, onDone }: { deliveryId: string; riders: AvailableRider[]; onDone: () => void }) {
  const [partnerId, setPartnerId] = useState("");
  return (
    <DispatchAction label="Reassign" confirmLabel="Reassign rider" canConfirm={Boolean(partnerId)}
      extra={<ReassignPicker riders={riders} value={partnerId} onChange={setPartnerId} />}
      onConfirm={async (reason) => { await adminDispatchApi.reassign(deliveryId, partnerId, reason); onDone(); }} />
  );
}

/** Admin dispatch control centre: live board, rider issues, and audited release/reassign/cancel actions. */
export default function Deliveries() {
  const [board, setBoard] = useState<AdminDispatchBoard | null>(null);
  const [issues, setIssues] = useState<DispatchIssue[]>([]);
  const [riders, setRiders] = useState<AvailableRider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const refresh = () => setRevision((current) => current + 1);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([adminDispatchApi.board(), adminDispatchApi.issues(), adminDispatchApi.riders()])
      .then(([boardData, issueData, riderData]) => {
        if (active) { setBoard(boardData); setIssues(issueData); setRiders(riderData); setError(null); }
      })
      .catch(() => { if (active) setError("Unable to load the dispatch board. Check administrator permissions."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [revision]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-display text-xl text-ink">Dispatch operations</h1>
          <RoutingHealth />
        </div>
        <Button variant="secondary" size="sm" disabled={loading} onClick={refresh}>Refresh</Button>
      </div>
      <ControlTower />
      {loading && <p role="status" className="text-sm text-ink-soft">Loading dispatch board…</p>}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {board && !error && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Card><p className="text-xs text-ink-soft">Awaiting rider</p>
              <p className="text-2xl font-medium">{board.unassigned_count}</p></Card>
            <Card><p className="text-xs text-ink-soft">Active deliveries</p>
              <p className="text-2xl font-medium">{board.active_count}</p></Card>
            <Card><p className="text-xs text-ink-soft">Verified riders online</p>
              <p className="text-2xl font-medium">{board.available_verified_riders}</p></Card>
            <Card className={board.open_issue_count > 0 ? "border-thread/40" : undefined}>
              <p className="text-xs text-ink-soft">Open rider issues</p>
              <p className={board.open_issue_count > 0 ? "text-2xl font-medium text-thread" : "text-2xl font-medium"}>{board.open_issue_count}</p></Card>
          </div>

          <section className="space-y-3" aria-label="Rider issues">
            <h2 className="font-display text-lg">Rider issues</h2>
            {issues.length === 0 && <p className="text-sm text-ink-soft">No open issues.</p>}
            {issues.map((issue) => (
              <Card key={issue.id} className="flex flex-col gap-2 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-medium text-ink">{ISSUE_LABEL[issue.issue_type] ?? issue.issue_type}</p>
                    <p className="text-xs text-ink-soft">{issue.order_number} · reported by {issue.rider_first_name} ·{" "}
                      <DateTimeDisplay value={issue.created_at} format="relative" />{issue.has_photo ? " · photo attached" : ""}</p>
                  </div>
                  <span className={issue.status === "OPEN"
                    ? "rounded-full bg-[#fbecea] px-2 py-0.5 text-[11px] font-medium text-thread"
                    : "rounded-full bg-[#e6ecff] px-2 py-0.5 text-[11px] font-medium text-[#2c3e9e]"}>
                    {issue.status === "OPEN" ? "Open" : "Investigating"}</span>
                </div>
                <p className="text-sm text-ink">{issue.description}</p>
                <div className="flex flex-wrap gap-2">
                  {issue.status === "OPEN" && (
                    <Button size="sm" variant="secondary"
                      onClick={async () => { await adminDispatchApi.updateIssue(issue.id, "INVESTIGATING"); refresh(); }}>
                      Mark investigating</Button>
                  )}
                  <DispatchAction label="Resolve" confirmLabel="Resolve issue" reasonLabel="Resolution note (sent to the rider)"
                    onConfirm={async (note) => { await adminDispatchApi.updateIssue(issue.id, "RESOLVED", note); refresh(); }} />
                </div>
              </Card>
            ))}
          </section>

          <section className="space-y-3" aria-label="Unassigned delivery requests">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-display text-lg">Waiting for a rider</h2>
              <span className="text-xs text-ink-soft">Auto-offers {board.auto_offers_enabled ? "on" : "off"}</span>
            </div>
            {board.pending.length === 0 && <p className="text-sm text-ink-soft">No requests awaiting assignment.</p>}
            {board.pending.map((request) => (
              <Card key={request.id} className="flex flex-col gap-2 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p>{orderLabel(request)}</p>
                  <span className="text-xs text-ink-soft">Requested <DateTimeDisplay value={request.created_at} format="relative" /></span>
                </div>
                {request.offered_to && request.offer_expires_at && (
                  <p className="text-xs text-[#2c3e9e]">
                    Offered to {request.offered_to} (attempt {request.offer_attempt}) · expires{" "}
                    <DateTimeDisplay value={request.offer_expires_at} format="relative" />
                  </p>
                )}
                <SuggestedRiders requestId={request.id} onAssigned={refresh} />
                <DispatchAction label="Stop rider search" confirmLabel="Stop search" variant="danger"
                  onConfirm={async (reason) => { await adminDispatchApi.cancelRequest(request.id, reason); refresh(); }} />
              </Card>
            ))}
          </section>

          <section className="space-y-3" aria-label="Active delivery assignments">
            <h2 className="font-display text-lg">Active rider assignments</h2>
            {board.active.length === 0 && <p className="text-sm text-ink-soft">No active rider assignments.</p>}
            {board.active.map((run) => {
              const collected = run.status !== "assigned";
              return (
                <Card key={run.id} className="flex flex-col gap-2 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p>{orderLabel(run)}</p>
                      <p className="text-xs text-ink-soft">
                        Rider {run.rider_first_name ?? "unknown"}{run.vehicle_type ? ` · ${run.vehicle_type}` : ""}
                        {run.open_issue_count > 0 && <span className="ml-1 font-medium text-thread">· {run.open_issue_count} open issue{run.open_issue_count > 1 ? "s" : ""}</span>}
                      </p>
                    </div>
                    <span className="flex flex-col items-end gap-0.5">
                      <span className="capitalize text-ink-soft">{run.status.replaceAll("_", " ")}</span>
                      {run.tracking && (
                        <span className={`text-xs ${["live", "delayed"].includes(run.tracking.state) ? "text-ink-soft" : "text-thread"}`}>
                          {describeFreshness(run.tracking.state, run.tracking.age_seconds).label}
                        </span>
                      )}
                    </span>
                  </div>
                  {collected ? (
                    <p className="text-xs text-ink-soft">Package collected. Handle problems through rider issues.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      <DispatchAction label="Release to job board" confirmLabel="Release rider" variant="danger"
                        onConfirm={async (reason) => { await adminDispatchApi.release(run.id, reason); refresh(); }} />
                      <ReassignAction deliveryId={run.id} riders={riders} onDone={refresh} />
                    </div>
                  )}
                  <DeliveryEventLog deliveryId={run.id} />
                  {run.delivery_partner_id && <RiderRouteToggle partnerId={run.delivery_partner_id} />}
                </Card>
              );
            })}
          </section>
          <p className="text-xs text-ink-soft">
            Shows the most recent 50 waiting and 100 active deliveries. Every action is recorded in the audit log;
            no payment or payout is changed.
          </p>
        </>
      )}
    </div>
  );
}

import { useEffect, useState, type FormEvent } from "react";
import { disputesApi, DISPUTE_REASONS, type Dispute, type DisputeReason } from "@/api/disputes.api";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const PAID = ["paid", "accepted", "in_production", "ready_for_delivery", "shipped", "out_for_delivery", "delivered",
  "received", "completed", "confirmed", "processing", "ready_for_pickup", "picked_up", "in_transit"];

/** Problems with an order. The buyer can report one (once paid); the seller sees what was reported
 * and how Tailora resolved it. */
export function OrderDispute({ orderId, orderStatus, isBuyer }: { orderId: string; orderStatus: string; isBuyer: boolean }) {
  const [disputes, setDisputes] = useState<Dispute[] | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [reason, setReason] = useState<DisputeReason | "">("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    disputesApi.forOrder(orderId).then((rows) => { if (active) setDisputes(Array.isArray(rows) ? rows : []); }).catch(() => { if (active) setDisputes([]); });
    return () => { active = false; };
  }, [orderId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!reason) { setError("Choose what went wrong."); return; }
    if (description.trim().length < 10) { setError("Tell us a little more (at least 10 characters)."); return; }
    setBusy(true); setError(null);
    try {
      const created = await disputesApi.open(orderId, reason, description.trim());
      setDisputes((rows) => [created, ...(rows ?? [])]);
      setFormOpen(false); setReason(""); setDescription("");
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't send your report. Try again."));
    } finally { setBusy(false); }
  }

  if (!disputes) return null;
  const isOpen = (d: Dispute) => d.status !== "resolved";
  const open = disputes.find(isOpen);
  const canReport = isBuyer && !open && PAID.includes(orderStatus);
  if (disputes.length === 0 && !canReport) return null;

  return (
    <section aria-label="Problems with this order" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
      <h2 className="font-semibold text-ink">{isBuyer ? "Problem with this order?" : "Reported problems"}</h2>
      {disputes.map((d) => (
        <div key={d.id} className={`rounded-control border p-3 text-sm ${isOpen(d) ? "border-warning/40 bg-warning-wash" : "border-line"}`}>
          <p className="font-medium text-ink">{d.reason_label} · {isOpen(d) ? "Being reviewed by Tailora" : `Resolved: ${d.outcome_label}`}</p>
          <p className="mt-1 text-ink-soft">{d.description}</p>
          {isOpen(d) && (
            <p className="mt-1 text-xs text-ink-soft">
              {isBuyer ? "Tailora will look into it and get back to you. The seller hasn't been paid for this order yet."
                : "Tailora will review it. Your payout for this order is on hold until then."}
            </p>
          )}
          {d.resolution_note && <p className="mt-2 text-ink"><span className="font-medium">Tailora's decision:</span> {d.resolution_note}</p>}
          {d.refund_amount != null && <p className="text-ink">Refund: {formatCurrency(d.refund_amount)}</p>}
        </div>
      ))}
      {canReport && !formOpen && (
        <Button variant="secondary" size="sm" className="self-start" onClick={() => setFormOpen(true)}>Report a problem</Button>
      )}
      {canReport && formOpen && (
        <form onSubmit={submit} className="flex flex-col gap-3" noValidate>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-ink">What went wrong?</span>
            <Select value={reason} onChange={(e) => setReason(e.target.value as DisputeReason)}>
              <option value="" disabled>Choose one</option>
              {DISPUTE_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </Select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-ink">Tell us more</span>
            <Textarea rows={4} maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. The trousers are about 5 cm too short, and the waist is loose." />
          </label>
          {error && <p role="alert" className="text-sm text-thread">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" size="sm" isLoading={busy}>Send to Tailora</Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => { setFormOpen(false); setError(null); }}>Cancel</Button>
          </div>
          <p className="text-xs text-ink-soft">The seller is told about the problem, and isn't paid for this order until Tailora has reviewed it.</p>
        </form>
      )}
    </section>
  );
}

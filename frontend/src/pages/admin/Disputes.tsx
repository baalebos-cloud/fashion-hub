import { useEffect, useState } from "react";
import { disputesApi, type Dispute, type DisputeOutcome } from "@/api/disputes.api";
import { endReviewWindow, hasReviewWindow, verificationApi } from "@/api/verification.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { isApiError } from "@/lib/api/errors";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const PAGE_SIZE = 50;
const FILTERS = [["open", "Open"], ["resolved", "Resolved"], ["", "All"]] as const;
const OUTCOMES: { value: DisputeOutcome; label: string; hint: string }[] = [
  { value: "remake", label: "Remake or alteration", hint: "The seller fixes or remakes it. No money moves." },
  { value: "refund", label: "Refund", hint: "Refund the buyer (all or part). Needs your authenticator code." },
  { value: "no_action", label: "No action", hint: "The complaint isn't upheld. Explain why." },
];

function Resolve({ dispute, onDone }: { dispute: Dispute; onDone: () => void }) {
  const [outcome, setOutcome] = useState<DisputeOutcome | "">("");
  const [note, setNote] = useState("");
  const [amount, setAmount] = useState(String(dispute.order_total ?? ""));
  const [code, setCode] = useState("");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!outcome) { setError("Choose an outcome."); return; }
    if (note.trim().length < 5) { setError("Explain the decision; both the buyer and the seller will see it."); return; }
    setBusy(true); setError(null);
    try {
      if (outcome === "refund" && !hasReviewWindow()) {
        if (!asking) { setAsking(true); setBusy(false); return; }
        await verificationApi.openReviewWindow(code);
      }
      await disputesApi.resolve(dispute.id, { outcome, note: note.trim(), ...(outcome === "refund" ? { refund_amount: amount } : {}) });
      onDone();
    } catch (err) {
      if (isApiError(err) && err.code === "step_up_required") { endReviewWindow(); setAsking(true); }
      setError(getDisplayErrorMessage(err, "The dispute couldn't be resolved."));
    } finally { setBusy(false); setCode(""); }
  }

  return (
    <div className="flex flex-col gap-3 border-t border-line pt-3">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium text-ink">Decision</legend>
        {OUTCOMES.map((o) => (
          <label key={o.value} className="flex items-start gap-2 text-sm">
            <input type="radio" name={`outcome-${dispute.id}`} value={o.value} checked={outcome === o.value}
              onChange={() => { setOutcome(o.value); setAsking(false); }} className="mt-1" />
            <span><span className="font-medium text-ink">{o.label}</span> <span className="text-ink-soft">{o.hint}</span></span>
          </label>
        ))}
      </fieldset>
      {outcome === "refund" && (
        <label className="flex max-w-xs flex-col gap-1 text-sm">
          <span className="font-medium text-ink">Refund amount (₦), up to {formatCurrency(dispute.order_total ?? 0, dispute.currency ?? "NGN")}</span>
          <Input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ""))} />
        </label>
      )}
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-ink">Note to the buyer and seller</span>
        <Textarea rows={3} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Measurements on the order show 104 cm; the tailor will alter the trousers free of charge by Friday." />
      </label>
      {asking && (
        <Input aria-label="Code from your authenticator app" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
          className="max-w-[10rem]" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code" />
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <Button size="sm" className="self-start" isLoading={busy} disabled={asking && code.length !== 6} onClick={() => void submit()}>
        {asking ? "Confirm with code" : "Resolve dispute"}
      </Button>
    </div>
  );
}

/** Problems buyers reported about paid orders. While one is open, the seller's payout is held. */
export default function Disputes() {
  const [status, setStatus] = useState<string>("open");
  const [items, setItems] = useState<Dispute[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [opened, setOpened] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    disputesApi.adminList({ status: status || undefined, page, page_size: PAGE_SIZE })
      .then((res) => { if (active) { setItems(res.items); setTotal(res.total); } })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Couldn't load disputes.")); });
    return () => { active = false; };
  }, [status, page, refresh]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl text-ink">Disputes {items && <span className="ml-2 text-sm font-normal text-ink-soft">({total})</span>}</h1>
        <div className="flex gap-1.5" role="group" aria-label="Filter">
          {FILTERS.map(([value, label]) => (
            <button key={value} type="button" aria-pressed={status === value} onClick={() => { if (value === status) return; setStatus(value); setPage(1); setItems(null); }}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${status === value ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink"}`}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <p className="text-sm text-ink-soft">Problems buyers reported about paid orders. While a dispute is open, the seller isn't paid for that order.</p>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {!items && !error && <p role="status">Loading disputes…</p>}
      {items && items.length === 0 && <EmptyState title={status === "open" ? "No open disputes" : "No disputes to show"} />}
      {items?.map((d) => (
        <Card key={d.id} className="flex flex-col gap-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold text-ink">{d.reason_label} · <span className="font-mono">{d.order_number}</span></span>
            {d.status === "resolving" ? <Badge tone="warning">Refund in progress</Badge> : d.status === "open" ? <Badge tone="warning">Open</Badge> : <Badge tone="success">Resolved: {d.outcome_label}</Badge>}
          </div>
          <p className="text-sm text-ink-soft">
            From {d.buyer_name ?? "the buyer"} about {d.seller_name ?? "the seller"} ·{" "}
            {d.order_type === "vendor_order" ? "materials" : "garment"} order of {formatCurrency(d.order_total ?? 0, d.currency ?? "NGN")}
            {d.created_at && <> · reported <DateTimeDisplay value={d.created_at} format="relative" /></>}
          </p>
          <p className="text-sm text-ink">{d.description}</p>
          {d.resolution_note && <p className="text-sm text-ink"><span className="font-medium">Decision:</span> {d.resolution_note}</p>}
          {d.refund_amount != null && <p className="text-sm text-ink">Refunded {formatCurrency(d.refund_amount, d.currency ?? "NGN")}</p>}
          {d.status !== "resolved" && (opened === d.id
            ? <Resolve dispute={d} onDone={() => { setOpened(null); setRefresh((n) => n + 1); }} />
            : <Button size="sm" variant="secondary" className="self-start" onClick={() => setOpened(d.id)}>Decide</Button>)}
        </Card>
      ))}
      {total > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={(p) => { setPage(p); setItems(null); }} />
      )}
    </div>
  );
}

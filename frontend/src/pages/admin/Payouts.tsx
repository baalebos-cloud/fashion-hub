import { useEffect, useState } from "react";
import { payoutsApi, type AdminPayout } from "@/api/payouts.api";
import { endReviewWindow, hasReviewWindow, verificationApi } from "@/api/verification.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { isApiError } from "@/lib/api/errors";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const FILTERS = [["held", "On hold"], ["failed", "Failed"], ["processing", "Sending"], ["pending", "Waiting"], ["paid", "Paid"], ["", "All"]] as const;

function Row({ payout, onDone }: { payout: AdminPayout; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [code, setCode] = useState("");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function release() {
    setBusy(true); setError(null);
    try {
      if (!hasReviewWindow()) {
        if (!asking) { setAsking(true); setBusy(false); return; }
        await verificationApi.openReviewWindow(code);
      }
      await payoutsApi.adminRelease(payout.id);
      onDone();
    } catch (err) {
      if (isApiError(err) && err.code === "step_up_required") { endReviewWindow(); setAsking(true); }
      setError(getDisplayErrorMessage(err, "The payout couldn't be released."));
    } finally { setBusy(false); setCode(""); }
  }

  async function hold() {
    setBusy(true); setError(null);
    try { await payoutsApi.adminHold(payout.id, reason); onDone(); }
    catch (err) { setError(getDisplayErrorMessage(err, "The payout couldn't be held.")); }
    finally { setBusy(false); }
  }

  return (
    <Card className="flex flex-col gap-2 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold text-ink">{payout.seller_name} · {formatCurrency(payout.net_amount, payout.currency)}</span>
        <Badge tone={payout.status === "paid" ? "success" : payout.status === "failed" ? "danger" : payout.status === "held" ? "warning" : "neutral"}>{payout.status}</Badge>
      </div>
      <p className="text-[13px] text-ink-soft">
        Order <span className="font-mono">{payout.order_number}</span> ({payout.order_status.replace(/_/g, " ")}) · created{" "}
        <DateTimeDisplay value={payout.created_at} format="relative" />{payout.attempts > 0 && ` · ${payout.attempts} attempt(s)`}
      </p>
      {payout.hold_reason && <p className="text-[13px] text-warning">On hold: {payout.hold_reason}</p>}
      {payout.failure_reason && <p className="text-[13px] text-thread">Failed: {payout.failure_reason}</p>}
      {(payout.status === "held" || payout.status === "failed") && (
        <div className="flex flex-wrap items-center gap-2">
          {asking && (
            <input aria-label="Code from your authenticator app" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code"
              className="min-h-9 w-32 rounded-control border border-line-strong bg-surface px-3 font-mono text-ink" />
          )}
          <Button size="sm" isLoading={busy} disabled={asking && code.length !== 6} onClick={() => void release()}>
            {asking ? "Confirm and release" : payout.status === "failed" ? "Retry" : "Release"}
          </Button>
        </div>
      )}
      {(payout.status === "pending" || payout.status === "failed") && (
        <div className="flex flex-wrap items-center gap-2">
          <input aria-label="Reason for holding" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason, e.g. customer complaint"
            className="min-h-9 flex-1 rounded-control border border-line-strong bg-surface px-3 text-sm text-ink" />
          <Button size="sm" variant="secondary" disabled={reason.trim().length < 3 || busy} onClick={() => void hold()}>Hold</Button>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
    </Card>
  );
}

/** Seller payouts: sent automatically after the customer confirms receipt; admins hold or release. */
export default function Payouts() {
  const [status, setStatus] = useState<string>("held");
  const [data, setData] = useState<{ payouts_enabled: boolean; items: AdminPayout[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    payoutsApi.adminList(status || undefined).then((d) => { if (active) { setData(d); setError(null); } })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Payouts couldn't be loaded.")); });
    return () => { active = false; };
  }, [status, tick]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-3xl text-ink">Payouts</h1>
        <p className="text-sm text-ink-soft">
          Sent automatically through Paystack once the customer confirms receipt and no refund or delivery problem is open.
          Releasing a held or failed payout needs a code from your authenticator app.
        </p>
        {data && !data.payouts_enabled && (
          <p className="rounded-control bg-warning-wash px-3 py-2 text-[13px] text-warning">
            Payouts are switched off (PAYOUTS_ENABLED). Nothing is sent until they're switched on.
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter payouts">
        {FILTERS.map(([value, label]) => (
          <Button key={value || "all"} size="sm" variant={status === value ? "primary" : "secondary"} role="tab"
            aria-selected={status === value} onClick={() => setStatus(value)}>{label}</Button>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {data && data.items.length === 0 && <EmptyState title="Nothing here" description="No payouts with this status." />}
      {data?.items.map((p) => <Row key={p.id} payout={p} onDone={() => setTick((t) => t + 1)} />)}
    </div>
  );
}

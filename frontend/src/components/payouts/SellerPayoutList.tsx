import { useEffect, useState } from "react";
import { payoutsApi, type SellerPayout } from "@/api/payouts.api";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import { formatCurrency } from "@/lib/formatters/currency";

const LABEL: Record<SellerPayout["status"], { text: string; tone: "neutral" | "warning" | "success" | "danger" }> = {
  pending: { text: "Waiting for the customer to confirm receipt", tone: "neutral" },
  processing: { text: "On its way to your bank", tone: "neutral" },
  paid: { text: "Paid", tone: "success" },
  held: { text: "On hold", tone: "warning" },
  failed: { text: "Didn't go through, Tailora will retry", tone: "danger" },
};

/** What the seller is owed per order after the platform commission, and where each payout is. */
export function SellerPayoutList() {
  const [rows, setRows] = useState<SellerPayout[] | null>(null);
  useEffect(() => { payoutsApi.mine().then(setRows).catch(() => setRows([])); }, []);
  if (!rows || rows.length === 0) return null;
  return (
    <div className="flex flex-col gap-3">
      <h2 className="font-semibold text-ink">Payouts</h2>
      {rows.map((p) => (
        <Card key={p.order_id} className="flex flex-col gap-1 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-sm text-ink">{formatCurrency(p.net_amount, p.currency)}</span>
            <Badge tone={LABEL[p.status].tone}>{LABEL[p.status].text}</Badge>
          </div>
          <p className="text-[13px] text-ink-soft">
            Order total {formatCurrency(p.gross_amount, p.currency)} · Tailora fee {formatCurrency(p.commission_amount, p.currency)}
            {p.paid_at && <> · paid <DateTimeDisplay value={p.paid_at} format="relative" /></>}
          </p>
          {p.status === "held" && p.hold_reason && <p className="text-[13px] text-warning">{p.hold_reason}</p>}
        </Card>
      ))}
    </div>
  );
}

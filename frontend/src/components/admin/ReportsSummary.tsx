import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { adminListsApi, type AdminReports } from "@/api/admin-lists.api";

const PERIODS = [7, 30, 90] as const;

function Tile({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <Card className="p-4">
      <div className="text-[13px] text-ink-soft">{label}</div>
      <div className="mt-1 font-display text-2xl text-ink">{value}</div>
      {note && <div className="mt-0.5 text-xs text-ink-soft">{note}</div>}
    </Card>
  );
}

/** Orders per day: one series, so one colour, thin bars from the baseline, a tooltip per bar and a
 * table of the same numbers for screen readers. */
function OrdersPerDay({ rows }: { rows: AdminReports["orders_per_day"] }) {
  const [showTable, setShowTable] = useState(false);
  const peak = Math.max(1, ...rows.map((r) => r.orders));
  if (rows.length === 0) return <p className="text-sm text-ink-soft">No orders in this period.</p>;
  const label = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en-NG", { day: "numeric", month: "short" });
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-40 items-end gap-0.5 border-b border-line" role="img"
        aria-label={`Orders per day, highest ${peak} on one day`}>
        {rows.map((r) => (
          <div key={r.date} className="group relative flex h-full flex-1 items-end justify-center">
            <div className="w-full max-w-4 rounded-t bg-indigo transition-opacity group-hover:opacity-80"
              style={{ height: `${Math.max(2, (r.orders / peak) * 100)}%` }} />
            <span className="pointer-events-none absolute bottom-full mb-1 hidden whitespace-nowrap rounded bg-ink px-2 py-1 text-xs text-paper group-hover:block">
              {label(r.date)}: {r.orders} order{r.orders === 1 ? "" : "s"}
            </span>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-ink-soft">
        <span>{label(rows[0].date)}</span><span>{label(rows[rows.length - 1].date)}</span>
      </div>
      <button type="button" className="self-start text-xs font-semibold text-indigo" onClick={() => setShowTable((v) => !v)}>
        {showTable ? "Hide numbers" : "Show as a table"}
      </button>
      {showTable && (
        <table className="text-sm">
          <thead><tr><th className="pr-6 text-left font-medium text-ink-soft">Day</th><th className="text-left font-medium text-ink-soft">Orders</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.date}><td className="pr-6">{label(r.date)}</td><td>{r.orders}</td></tr>)}</tbody>
        </table>
      )}
    </div>
  );
}

/** Real figures for the Reports page: sales, orders and verification for the chosen period. */
export function ReportsSummary() {
  const [days, setDays] = useState<number>(30);
  const [data, setData] = useState<AdminReports | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    adminListsApi.reports(days)
      .then((value) => { if (active) setData(value); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err, "Couldn't load the reports.")); });
    return () => { active = false; };
  }, [days, attempt]);

  return (
    <section aria-labelledby="sales-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="sales-heading" className="font-display text-lg text-ink">Sales and orders</h2>
        <div className="flex gap-1.5" role="group" aria-label="Period">
          {PERIODS.map((p) => (
            <button key={p} type="button" aria-pressed={days === p} onClick={() => { if (p === days) return; setDays(p); setData(null); }}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium ${days === p ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:border-ink"}`}>
              Last {p} days
            </button>
          ))}
        </div>
      </div>
      {error && (
        <div className="flex flex-col items-start gap-2">
          <p role="alert" className="text-sm text-thread">{error}</p>
          <Button variant="secondary" size="sm" onClick={() => setAttempt((n) => n + 1)}>Try again</Button>
        </div>
      )}
      {!data && !error && <p role="status" className="text-sm text-ink-soft">Loading reports…</p>}
      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Tile label="Sales (paid orders)" value={formatCurrency(data.gmv, data.currency)} note="Garments and materials" />
            <Tile label="Garment orders" value={data.garment_orders.placed}
              note={`${data.garment_orders.paid} paid · ${data.garment_orders.completed} completed`} />
            <Tile label="Material orders" value={data.material_orders.placed}
              note={`${data.material_orders.paid} paid · ${data.material_orders.completed} completed`} />
            <Tile label="Cancelled or refunded" value={data.garment_orders.cancelled + data.material_orders.cancelled} />
          </div>
          <Card className="p-4">
            <h3 className="mb-3 text-sm font-medium text-ink">Orders per day</h3>
            <OrdersPerDay rows={data.orders_per_day} />
          </Card>
          <div className="grid gap-3 md:grid-cols-2">
            {([["Identity checks (NIN)", data.identity_checks], ["Business checks (CAC)", data.business_checks]] as const).map(([name, f]) => (
              <Card key={name} className="p-4">
                <h3 className="text-sm font-medium text-ink">{name}</h3>
                <p className="mt-1 text-sm text-ink-soft">
                  {f.submitted} submitted · {f.verified} verified · {f.rejected} rejected · {f.waiting} waiting
                </p>
                {f.submitted > 0 && (
                  <p className="mt-1 text-xs text-ink-soft">{Math.round((f.verified / f.submitted) * 100)}% verified so far</p>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

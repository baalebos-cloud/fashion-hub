import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "@/api/orders.api";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Button } from "@/components/ui/button";
import { professionalRoutes } from "@/config/routes.config";
import { formatCurrency } from "@/lib/formatters/currency";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Order } from "@/types/order";

// Matches the backend: materials can be linked while the garment is being prepared,
// and only before the material purchase is paid.
const CAN_SOURCE = ["paid", "accepted", "in_production"];
const LINKABLE = ["cart", "checkout", "payment_pending"];

/** Material purchases for one customer order, with a way to link an unpaid purchase to it. */
export function OrderMaterials({ order }: { order: Order }) {
  const [purchases, setPurchases] = useState<Order[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    ordersApi.listAll({ perspective: "buying", order_type: "vendor_order" })
      .then((list) => { if (active) { setPurchases(list); setFailed(false); } })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [revision]);

  const linked = (purchases ?? []).filter((p) => p.parent_customer_order_id === order.id);
  const linkable = CAN_SOURCE.includes(order.status)
    ? (purchases ?? []).filter((p) => !p.parent_customer_order_id && LINKABLE.includes(p.status))
    : [];

  async function link() {
    if (!choice) return;
    setBusy(true); setError(null);
    try {
      await ordersApi.linkMaterial(order.id, choice);
      setChoice("");
      setRevision((n) => n + 1);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "That material order couldn't be linked."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Materials for this order" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-ink">Materials for this order</h2>
        <Link to={professionalRoutes.vendorMarketplace} className="text-sm font-semibold text-indigo">Buy materials</Link>
      </div>
      {failed && <p className="text-sm text-ink-soft">Your material orders couldn't be loaded.</p>}
      {purchases && linked.length === 0 && <p className="text-sm text-ink-soft">No material orders linked yet.</p>}
      {linked.length > 0 && (
        <ul className="flex flex-col divide-y divide-line">
          {linked.map((m) => (
            <li key={m.id}>
              <Link to={professionalRoutes.vendorOrderDetails(m.id)} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-semibold text-ink">{m.items[0]?.name_snapshot ?? m.order_number}</span>
                  <span className="font-mono text-xs text-ink-soft">{m.order_number} · {formatCurrency(m.total_amount, m.currency)}</span>
                </span>
                <OrderStatusBadge status={m.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {linkable.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <label htmlFor={`link-${order.id}`} className="text-sm font-semibold text-ink">Link a material order you haven't paid for yet</label>
          <div className="flex flex-wrap gap-2">
            <select id={`link-${order.id}`} value={choice} onChange={(e) => setChoice(e.target.value)}
              className="min-h-11 min-w-0 flex-1 rounded-control border border-line-strong bg-surface px-3 text-ink focus:border-indigo focus:outline-none">
              <option value="">Choose a material order…</option>
              {linkable.map((m) => (
                <option key={m.id} value={m.id}>{m.order_number} · {m.items[0]?.name_snapshot ?? "Materials"}</option>
              ))}
            </select>
            <Button variant="secondary" disabled={!choice} isLoading={busy} onClick={() => void link()}>Link</Button>
          </div>
          <p className="text-[13px] text-ink-soft">Linking only records which garment the materials are for. Once linked it can't be moved to another order.</p>
          {error && <p role="alert" className="text-sm text-thread">{error}</p>}
        </div>
      )}
    </section>
  );
}

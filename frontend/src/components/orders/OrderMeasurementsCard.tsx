import { useEffect, useState } from "react";
import { ordersApi } from "@/api/orders.api";
import { isApiError } from "@/lib/api/errors";
import { Badge } from "@/components/ui/badge";
import type { OrderMeasurements } from "@/types/order";

const label = (name: string) => name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

/** The customer's measurements as saved on this order. The backend decides who may see them and when. */
export function OrderMeasurementsCard({ orderId, status }: { orderId: string; status: string }) {
  const [data, setData] = useState<OrderMeasurements | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "locked" | "missing" | "error">("loading");

  useEffect(() => {
    let active = true;
    setState("loading");
    ordersApi.measurements(orderId)
      .then((value) => { if (active) { setData(value); setState("ready"); } })
      .catch((err) => {
        if (!active) return;
        if (isApiError(err) && err.status === 403) setState("locked");
        else if (isApiError(err) && err.status === 404) setState("missing");
        else setState("error");
      });
    return () => { active = false; };
  }, [orderId, status]);

  return (
    <section aria-label="Customer measurements" className="flex flex-col gap-3 rounded-card border border-line bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold text-ink">Customer measurements</h2>
        {data?.label && <Badge tone="neutral">{data.label}</Badge>}
      </div>
      {state === "loading" && <p role="status" className="text-sm text-ink-soft">Loading measurements…</p>}
      {state === "locked" && (
        <p className="text-sm text-ink-soft">
          {status === "pending" ? "You'll see the measurements once the customer has paid." : "Measurements are no longer shown now this order is closed."}
        </p>
      )}
      {state === "missing" && <p className="text-sm text-ink-soft">No measurements were saved with this order. Ask the customer in Messages.</p>}
      {state === "error" && <p role="alert" className="text-sm text-thread">Measurements couldn't be loaded. Refresh the page to try again.</p>}
      {state === "ready" && data && (
        <>
          {data.fields.length === 0 ? (
            <p className="text-sm text-ink-soft">The saved profile has no values. Ask the customer in Messages.</p>
          ) : (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
              {data.fields.map((f) => (
                <div key={f.field_name} className="flex flex-col border-b border-line pb-2">
                  <dt className="text-[13px] text-ink-soft">{label(f.field_name)}</dt>
                  <dd className="font-mono text-ink">{Number(f.value).toString()} {f.unit}</dd>
                </div>
              ))}
            </dl>
          )}
          <p className="text-[13px] text-ink-soft">
            Saved when the order was placed{data.garment_type ? ` · for ${data.garment_type}` : ""}. Later changes to the customer's profile don't change this order.
          </p>
        </>
      )}
    </section>
  );
}

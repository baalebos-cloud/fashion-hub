import { useEffect, useRef, useState } from "react";
import { inventoryApi } from "@/api/inventory.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { LOW_STOCK_THRESHOLD } from "@/constants/order-status";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { cn } from "@/lib/utils/cn";
import type { Inventory as InventoryRecord } from "@/types/product";

function StockBadge({ available }: { available: number }) {
  if (available === 0) return <Badge tone="danger">Out of stock</Badge>;
  if (available <= LOW_STOCK_THRESHOLD) return <Badge tone="warning">Low</Badge>;
  return <Badge tone="success">In stock</Badge>;
}

function StockRow({ value, onRestocked }: { value: InventoryRecord; onRestocked: (value: InventoryRecord) => void }) {
  const [quantity, setQuantity] = useState(1);
  // One idempotency key per quantity, so a retried restock can't add stock twice.
  const keys = useRef(new Map<number, string>());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const valid = Number.isSafeInteger(quantity) && quantity >= 1 && quantity <= 1000000000;

  async function restock() {
    setSaving(true); setError(null); setDone(null);
    if (!keys.current.has(quantity)) keys.current.set(quantity, crypto.randomUUID());
    try {
      onRestocked(await inventoryApi.restock(value.product_variant_id, quantity, keys.current.get(quantity)!));
      keys.current.delete(quantity);
      setDone(`Added ${quantity}.`);
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const inputId = `restock-${value.id}`;
  return (
    <li className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate font-semibold text-ink">
          {value.product_name ?? "Product"}{value.colour && <span className="font-normal text-ink-soft"> · {value.colour}</span>}
        </span>
        <span className="font-mono text-xs text-ink-soft">{value.sku}</span>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <StockBadge available={value.quantity_available} />
          <span className="text-ink-soft">Available <span className="font-mono text-ink">{value.quantity_available}</span></span>
          <span className="text-ink-soft">Held for orders <span className="font-mono text-ink">{value.quantity_reserved}</span></span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor={inputId} className="text-[13px] font-semibold text-ink">Add to stock</label>
        <div className="flex gap-2">
          <Input id={inputId} type="number" inputMode="numeric" min={1} max={1000000000} step={1} value={quantity}
            className="w-28" onChange={(event) => setQuantity(Number(event.target.value))} />
          <Button variant="secondary" isLoading={saving} disabled={!valid} onClick={() => { void restock(); }}>Restock</Button>
        </div>
        {error && <p role="alert" className="text-[13px] text-thread">{error}</p>}
        {done && <p role="status" className="text-[13px] text-success">{done}</p>}
      </div>
    </li>
  );
}

/** Every stock line, lowest first, with an inline restock. */
export default function Inventory() {
  const [rows, setRows] = useState<InventoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [lowOnly, setLowOnly] = useState(false);
  // Rows restocked while filtering stay in view, so the confirmation doesn't vanish with them.
  const [restocked, setRestocked] = useState<Set<string>>(new Set());

  useEffect(() => {
    let active = true; setLoading(true); setError(null);
    inventoryApi.listAll()
      .then((values) => { if (active) setRows(values); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  const lowCount = rows.filter((r) => r.quantity_available <= LOW_STOCK_THRESHOLD).length;
  const shown = rows.filter((r) => !lowOnly || r.quantity_available <= LOW_STOCK_THRESHOLD || restocked.has(r.id))
    .sort((a, b) => a.quantity_available - b.quantity_available);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-3xl text-ink">Inventory</h1>
        <p className="text-sm text-ink-soft">
          Lowest stock first. "Low" means {LOW_STOCK_THRESHOLD} or fewer left. Stock held for paid orders isn't counted as available.
        </p>
      </div>

      {loading && <SkeletonRows rows={4} label="Loading stock" onRetry={() => setAttempt((n) => n + 1)} />}
      {!loading && error && <ErrorState title="Couldn't load your stock" description={error} onRetry={() => setAttempt((n) => n + 1)} />}

      {!loading && !error && rows.length === 0 && (
        <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">
          No stock yet. Add a product and its starting stock shows up here.
        </p>
      )}

      {!loading && !error && rows.length > 0 && (
        <>
          <div role="group" aria-label="Filter stock" className="flex gap-2">
            {[["All", false, rows.length], ["Low or out", true, lowCount]].map(([label, value, count]) => (
              <button key={label as string} type="button" aria-pressed={lowOnly === value} onClick={() => { setLowOnly(value as boolean); setRestocked(new Set()); }}
                className={cn("flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold",
                  lowOnly === value ? "border-indigo bg-indigo-wash text-indigo" : "border-line-strong bg-surface text-ink")}>
                {label}<span className="font-mono text-xs">{count as number}</span>
              </button>
            ))}
          </div>
          {shown.length === 0 ? (
            <p className="rounded-card border border-dashed border-line-strong bg-surface p-6 text-center text-sm text-ink-soft">Nothing is low on stock.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
              {shown.map((value) => (
                <StockRow key={value.id} value={value}
                  onRestocked={(updated) => {
                    setRestocked((ids) => new Set(ids).add(value.id));
                    setRows((values) => values.map((row) => (row.id === updated.id ? { ...row, ...updated } : row)));
                  }} />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

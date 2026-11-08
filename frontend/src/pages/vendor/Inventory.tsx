import { useEffect, useRef, useState } from "react";
import { inventoryApi } from "@/api/inventory.api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorState } from "@/components/ui/error-state";
import { SkeletonRows } from "@/components/ui/skeleton";
import { useLowStockThreshold } from "@/hooks/use-low-stock-threshold";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { cn } from "@/lib/utils/cn";
import type { Inventory as InventoryRecord } from "@/types/product";

function StockBadge({ available, threshold }: { available: number; threshold: number }) {
  if (available === 0) return <Badge tone="danger">Out of stock</Badge>;
  if (available <= threshold) return <Badge tone="warning">Low</Badge>;
  return <Badge tone="success">In stock</Badge>;
}

function StockRow({ value, threshold, onRestocked }: { value: InventoryRecord; threshold: number; onRestocked: (value: InventoryRecord) => void }) {
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
        <span className="truncate font-semibold text-ink">{value.product_name ?? "Product"}</span>
        <span className="font-mono text-xs text-ink-soft">{value.sku}</span>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <StockBadge available={value.quantity_available} threshold={threshold} />
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

function StockAlertSetting({ threshold, onSave }: { threshold: number; onSave: (value: number) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(threshold));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const number = Number(value);
  const valid = value.trim() !== "" && Number.isSafeInteger(number) && number >= 0 && number <= 1000000;

  async function submit() {
    setSaving(true); setError(null);
    try { await onSave(number); setEditing(false); }
    catch (err) { setError(getDisplayErrorMessage(err, "The alert level couldn't be saved.")); }
    finally { setSaving(false); }
  }

  return (
    <section aria-label="Low stock alert" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-4">
      {!editing ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-ink">
            <span className="font-semibold">Low stock alert:</span>{" "}
            {threshold === 0 ? "only when something is out of stock." : <><span className="font-mono">{threshold}</span> or fewer left.</>}
          </p>
          <Button size="sm" variant="secondary" onClick={() => { setValue(String(threshold)); setEditing(true); }}>Change</Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor="low-stock-threshold" className="text-sm font-semibold text-ink">Mark stock as low at or below</label>
          <div className="flex flex-wrap gap-2">
            <Input id="low-stock-threshold" type="number" inputMode="numeric" min={0} max={1000000} step={1} className="w-32"
              value={value} onChange={(e) => setValue(e.target.value)} error={valid ? undefined : "Enter a whole number, 0 or more."} />
            <Button size="sm" isLoading={saving} disabled={!valid} onClick={() => void submit()}>Save</Button>
            <Button size="sm" variant="ghost" disabled={saving} onClick={() => { setEditing(false); setError(null); }}>Cancel</Button>
          </div>
          <p className="text-[13px] text-ink-soft">Use 0 to be told only when something runs out.</p>
          {error && <p role="alert" className="text-sm text-thread">{error}</p>}
        </div>
      )}
    </section>
  );
}

/** Every stock line, lowest first, with an inline restock. */
export default function Inventory() {
  const [rows, setRows] = useState<InventoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [lowOnly, setLowOnly] = useState(false);
  const { threshold, save } = useLowStockThreshold();
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

  const lowCount = rows.filter((r) => r.quantity_available <= threshold).length;
  const shown = rows.filter((r) => !lowOnly || r.quantity_available <= threshold || restocked.has(r.id))
    .sort((a, b) => a.quantity_available - b.quantity_available);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="font-display text-3xl text-ink">Inventory</h1>
        <p className="text-sm text-ink-soft">
          Lowest stock first. Stock held for paid orders isn't counted as available.
        </p>
      </div>
      <StockAlertSetting threshold={threshold} onSave={save} />

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
                <StockRow key={value.id} value={value} threshold={threshold}
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

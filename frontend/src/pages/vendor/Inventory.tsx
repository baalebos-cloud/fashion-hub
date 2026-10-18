import { useEffect, useRef, useState } from "react";
import { inventoryApi } from "@/api/inventory.api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Inventory as InventoryRecord } from "@/types/product";

function StockRow({ value, onRestocked }: { value: InventoryRecord; onRestocked: (value: InventoryRecord) => void }) {
  const [quantity, setQuantity] = useState(1);
  const keys = useRef(new Map<number, string>());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function restock() {
    setSaving(true); setError(null);
    if (!keys.current.has(quantity)) keys.current.set(quantity, crypto.randomUUID());
    try {
      onRestocked(await inventoryApi.restock(value.product_variant_id, quantity, keys.current.get(quantity)!));
      keys.current.delete(quantity);
    }
    catch (err) { setError(getDisplayErrorMessage(err)); }
    finally { setSaving(false); }
  }
  return <li className="flex flex-col gap-2 rounded border border-line p-4">
    <p>{value.product_name} — {value.sku}</p>
    <p>Available: {value.quantity_available} · Reserved: {value.quantity_reserved}</p>
    <label htmlFor={`restock-${value.id}`}>Quantity to add</label>
    <Input id={`restock-${value.id}`} type="number" min={1} max={1000000000} step={1} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} />
    <Button isLoading={saving} disabled={!Number.isSafeInteger(quantity) || quantity < 1 || quantity > 1000000000} onClick={() => { void restock(); }}>Restock</Button>
    {error && <p role="alert">{error}</p>}
  </li>;
}
export default function Inventory() {
  const [inventory, setInventory] = useState<InventoryRecord[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true; setLoading(true); setError(null);
    inventoryApi.list(page).then((values) => { if (active) setInventory(values); }).catch((err) => { if (active) setError(getDisplayErrorMessage(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page]);
  return <div className="flex max-w-lg flex-col gap-5">
    <h1 className="font-display text-xl">Inventory</h1>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Loading stock…</p> : <ul className="flex flex-col gap-4">{inventory.map((value) => <StockRow key={value.id} value={value} onRestocked={(updated) => setInventory((values) => values.map((row) => row.id === updated.id ? updated : row))} />)}</ul>}
    {!loading && inventory.length === 0 && <p>No inventory on this page. Add a product first.</p>}
    <div className="flex gap-4"><Button disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page}</span><Button disabled={loading || inventory.length < 20} onClick={() => setPage((value) => value + 1)}>Next</Button></div>
  </div>;
}

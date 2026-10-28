import { useState } from "react";
import { Link } from "react-router-dom";
import { commerceApi, type CatalogRecommendation } from "@/api/commerce.api";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { professionalRoutes } from "@/config/routes.config";

/** Deterministic catalog guidance; does not promise inventory or a purchase. */
export function CatalogBudgetGuide() {
  const [budget, setBudget] = useState("");
  const [items, setItems] = useState<CatalogRecommendation[]>([]);
  const [requested, setRequested] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    const amount = Number(budget);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Enter a valid budget in naira.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await commerceApi.recommendations(amount);
      setItems(result.items);
      setRequested(true);
    } catch (exception) {
      setItems([]);
      setRequested(false);
      setError(getDisplayErrorMessage(exception));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-line p-4" aria-label="Material budget guide">
      <h2 className="mb-2 font-display text-lg text-ink">Find materials within your budget</h2>
      <p className="mb-3 text-sm text-ink-soft">
        Browse verified vendor listings with stock reported in the catalog.
        Final availability and total are confirmed at checkout.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-sm" htmlFor="material-budget">
          Budget (NGN)
          <input
            id="material-budget"
            type="number"
            min="1"
            step="0.01"
            value={budget}
            onChange={(event) => setBudget(event.target.value)}
            className="rounded-lg border border-line bg-white px-3 py-2"
            placeholder="15000"
          />
        </label>
        <Button onClick={() => { void search(); }} isLoading={loading} disabled={loading}>
          Recommend materials
        </Button>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-thread">{error}</p>}
      {requested && !loading && items.length === 0 && (
        <p role="status" className="mt-3 text-sm text-ink-soft">
          No verified in-stock catalog matches were found within this budget.
        </p>
      )}
      {items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li key={item.product_id} className="flex flex-wrap items-center justify-between gap-2">
              <Link className="underline" to={professionalRoutes.vendorProductDetails(item.product_id)}>
                {item.title}
              </Link>
              <span className="text-sm">₦{Number(item.price_ngn).toLocaleString("en-NG")}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

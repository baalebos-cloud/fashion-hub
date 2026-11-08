import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { searchApi, type SmartSearchResult } from "@/api/search.api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import { trackSearch } from "@/lib/tracking/interactions";

function budgetLabel({ min_price: low, max_price: high }: SmartSearchResult["filters"]): string | null {
  if (low != null && high != null) return `${formatCurrency(low)} – ${formatCurrency(high)}`;
  if (high != null) return `Up to ${formatCurrency(high)}`;
  if (low != null) return `From ${formatCurrency(low)}`;
  return null;
}

/** "Describe what you want": free text to designs, showing what was understood. */
export function SmartDesignSearch({ profilePathFor }: { profilePathFor: (professionalId: string) => string }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<SmartSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const query = text.trim();
    if (query.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await searchApi.smart(query));
      trackSearch(query, "smart_search");
    } catch {
      setResult(null);
      setError("Search isn't available right now. Try again in a moment.");
    } finally {
      setLoading(false);
    }
  }

  const budget = result ? budgetLabel(result.filters) : null;
  const understood = result ? [...result.filters.keywords, ...(budget ? [budget] : [])] : [];

  return (
    <section aria-label="Search designs in your own words" className="flex flex-col gap-3 rounded-xl border border-line p-4">
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1 text-sm text-ink" htmlFor="smart-search">
          Describe what you want
          <input id="smart-search" value={text} maxLength={200} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. blue agbada under 50k"
            className="rounded-lg border border-line bg-white px-3 py-2 text-ink" />
        </label>
        <Button type="submit" isLoading={loading} disabled={loading || text.trim().length < 2}>Search designs</Button>
      </form>
      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {result && (
        <div className="flex flex-col gap-3" role="status">
          {understood.length > 0 ? (
            <p className="flex flex-wrap items-center gap-1.5 text-xs text-ink-soft">
              Searching for
              {understood.map((term) => (
                <span key={term} className="rounded-full bg-muslin px-2 py-0.5 text-ink">{term}</span>
              ))}
              <span>· {result.understood_by === "ai" ? "understood by AI" : "matched by keywords"}</span>
            </p>
          ) : (
            <p className="text-sm text-ink-soft">Add a garment, fabric, colour or budget, e.g. "lace kaftan under 40k".</p>
          )}
          {understood.length > 0 && result.designs.length === 0 && (
            <p className="text-sm text-ink-soft">No designs match yet. Try fewer words or a wider budget.</p>
          )}
          {result.designs.length > 0 && (
            <ul className="grid gap-3 sm:grid-cols-2">
              {result.designs.map((design) => (
                <li key={design.id}>
                  <Link to={`${profilePathFor(design.professional_id)}?from=smart_search`} className="block h-full">
                    <Card className="flex h-full flex-col gap-1 p-3 transition-colors hover:border-brass">
                      <span className="font-medium text-ink">{design.title}</span>
                      {design.professional_name && <span className="text-xs text-ink-soft">by {design.professional_name}</span>}
                      {design.description && <span className="line-clamp-2 text-sm text-ink-soft">{design.description}</span>}
                      <span className="mt-auto text-sm font-medium text-ink">{formatCurrency(design.base_price, design.currency)}</span>
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/formatters/currency";
import type { RelatedProduct, RelatedReason } from "@/api/recommendations.api";

const REASON_LABEL: Record<RelatedReason, string> = {
  bought_together: "Often bought together",
  viewed_together: "Shoppers also viewed",
  similar: "Similar item",
  same_vendor: "From the same shop",
  for_you: "Picked for you",
  trending: "Popular now",
  new_in: "New in",
};

type Props = {
  title: string;
  /** Loads the row; called again when `loadKey` changes. */
  load: () => Promise<RelatedProduct[]>;
  loadKey: string;
  detailsPathFor: (productId: string) => string;
  /** Recorded as the source of the view when someone opens a suggestion. */
  source: string;
};

/** A row of related products. Hidden while loading, when empty, or if loading fails:
 * suggestions are a bonus, never something to show an error about. */
export function RelatedProducts({ title, load, loadKey, detailsPathFor, source }: Props) {
  const [items, setItems] = useState<RelatedProduct[]>([]);

  useEffect(() => {
    let active = true;
    setItems([]);
    load().then((value) => { if (active) setItems(value); }).catch(() => { /* hide the row */ });
    return () => { active = false; };
    // `load` is recreated on every render; `loadKey` says when the inputs really changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadKey]);

  if (items.length === 0) return null;
  return (
    <section aria-label={title} className="flex flex-col gap-3">
      <h2 className="font-display text-lg text-ink">{title}</h2>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map((item) => (
          <li key={item.product_id}>
            <Link to={`${detailsPathFor(item.product_id)}?from=${source}`} className="block h-full">
              <Card className="flex h-full flex-col gap-1.5 p-3 transition-colors hover:border-brass">
                <div className="aspect-square w-full overflow-hidden rounded-lg bg-muslin">
                  {item.primary_image_url && (
                    <img src={item.primary_image_url} alt={item.name} loading="lazy" className="h-full w-full object-cover" />
                  )}
                </div>
                <span className="text-sm font-medium text-ink">{item.name}</span>
                <span className="text-xs text-ink-soft">{item.vendor_name}</span>
                <span className="text-sm text-ink">
                  {formatCurrency(item.price_ngn, item.currency)}
                  <span className="text-xs text-ink-soft"> / {item.unit_of_measure}</span>
                </span>
                <span className={item.learned
                  ? "mt-auto self-start rounded-full bg-[#e6ecff] px-2 py-0.5 text-[11px] font-medium text-[#2c3e9e]"
                  : "mt-auto self-start rounded-full bg-muslin px-2 py-0.5 text-[11px] text-ink-soft"}>
                  {REASON_LABEL[item.reason]}
                </span>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

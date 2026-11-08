import { cn } from "@/lib/utils/cn";
import type { ProductVariant } from "@/types/product";

export function ProductVariantSelector({ variants, selectedId, onSelect }: { variants: ProductVariant[]; selectedId: string | null; onSelect: (variantId: string) => void }) {
  // A product sold in a single named colour still says which colour it is.
  if (variants.length === 1 && variants[0].attributes?.color) {
    return <p className="text-sm text-ink"><span className="font-semibold">Colour:</span> {variants[0].attributes.color}</p>;
  }
  if (variants.length <= 1) return null;

  return (
    <div>
      <div className="mb-1.5 text-sm font-semibold text-ink">{variants.every((v) => v.attributes?.color) ? "Colour" : "Options"}</div>
      <div className="flex flex-wrap gap-2">
        {variants.map((variant) => {
          const label = variant.attributes ? Object.values(variant.attributes).join(" / ") : variant.sku;
          return (
            <button
              key={variant.id}
              type="button"
              aria-pressed={selectedId === variant.id}
              onClick={() => onSelect(variant.id)}
              className={cn(
                "min-h-11 rounded-full border px-4 text-sm font-semibold",
                selectedId === variant.id ? "border-indigo bg-indigo-wash text-indigo" : "border-line-strong bg-surface text-ink hover:border-indigo"
              )}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

import { cn } from "@/lib/utils/cn";
import type { ProductVariant } from "@/types/product";

export function ProductVariantSelector({ variants, selectedId, onSelect }: { variants: ProductVariant[]; selectedId: string | null; onSelect: (variantId: string) => void }) {
  if (variants.length <= 1) return null;

  return (
    <div>
      <div className="mb-1.5 text-sm font-medium text-ink">Options</div>
      <div className="flex flex-wrap gap-2">
        {variants.map((variant) => {
          const label = variant.attributes ? Object.values(variant.attributes).join(" / ") : variant.sku;
          return (
            <button
              key={variant.id}
              onClick={() => onSelect(variant.id)}
              className={cn(
                "rounded-lg border px-3 py-1.5 text-sm",
                selectedId === variant.id ? "border-brass bg-muslin text-ink" : "border-line text-ink-soft hover:border-brass"
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

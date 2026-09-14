import { cn } from "@/lib/utils/cn";
import type { Category } from "@/api/categories.api";

export function VendorCategories({ categories, selectedId, onSelect }: { categories: Category[]; selectedId: string | null; onSelect: (id: string | null) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={() => onSelect(null)}
        className={cn("rounded-full border px-3 py-1.5 text-sm", !selectedId ? "border-brass bg-muslin text-ink" : "border-line text-ink-soft")}
      >
        All
      </button>
      {categories.map((category) => (
        <button
          key={category.id}
          onClick={() => onSelect(category.id)}
          className={cn(
            "rounded-full border px-3 py-1.5 text-sm",
            selectedId === category.id ? "border-brass bg-muslin text-ink" : "border-line text-ink-soft"
          )}
        >
          {category.name}
        </button>
      ))}
    </div>
  );
}

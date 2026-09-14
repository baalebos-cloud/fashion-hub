import { DesignCard } from "./DesignCard";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import type { Design } from "@/types/design";

export function DesignGallery({ designs, isLoading, onSelect }: { designs: Design[]; isLoading?: boolean; onSelect?: (designId: string) => void }) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  if (designs.length === 0) {
    return <EmptyState title="No designs listed yet" />;
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {designs.map((design) => (
        <DesignCard key={design.id} design={design} onSelect={onSelect ? () => onSelect(design.id) : undefined} />
      ))}
    </div>
  );
}

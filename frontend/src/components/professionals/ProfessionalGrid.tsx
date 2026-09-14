import { useState } from "react";
import { ProfessionalCard } from "./ProfessionalCard";
import { Pagination } from "@/components/ui/pagination";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { Professional } from "@/types/professional";

export interface ProfessionalGridProps {
  professionals: Professional[];
  total: number;
  isLoading: boolean;
  detailsPathFor: (id: string) => string;
  pageSize?: number;
  onPageChange?: (page: number) => void;
}

export function ProfessionalGrid({ professionals, total, isLoading, detailsPathFor, pageSize = 20, onPageChange }: ProfessionalGridProps) {
  const [page, setPage] = useState(1);

  function handlePageChange(next: number) {
    setPage(next);
    onPageChange?.(next);
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-40" />
        ))}
      </div>
    );
  }

  if (professionals.length === 0) {
    return <EmptyState title="No matches found" description="Try widening your search radius or filters." />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {professionals.map((professional) => (
          <ProfessionalCard key={professional.id} professional={professional} detailsPath={detailsPathFor(professional.id)} />
        ))}
      </div>
      {total > pageSize && <Pagination page={page} pageSize={pageSize} total={total} onPageChange={handlePageChange} />}
    </div>
  );
}

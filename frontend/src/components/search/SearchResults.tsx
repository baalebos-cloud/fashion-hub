import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import type { Professional } from "@/types/professional";

export function SearchResults({ professionals, isLoading, detailsPathFor }: { professionals: Professional[]; isLoading: boolean; detailsPathFor: (id: string) => string }) {
  return <ProfessionalGrid professionals={professionals} total={professionals.length} isLoading={isLoading} detailsPathFor={detailsPathFor} />;
}

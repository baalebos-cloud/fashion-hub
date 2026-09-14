import { useEffect, useState } from "react";
import { professionalsApi } from "@/api/professionals.api";
import { ProfessionalSearch } from "@/components/professionals/ProfessionalSearch";
import { ProfessionalFilters, type ProfessionalFiltersValue } from "@/components/professionals/ProfessionalFilters";
import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import { NearbyProfessionals } from "@/components/search/NearbyProfessionals";
import { customerRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";

export default function FindProfessionals() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<ProfessionalFiltersValue>({ radiusKm: 10 });
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    professionalsApi
      .list({ query, professionalType: filters.professionalType, radiusKm: filters.radiusKm })
      .then((response) => {
        setProfessionals(response.items);
        setTotal(response.total);
      })
      .finally(() => setIsLoading(false));
  }, [query, filters]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Find a professional</h1>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ProfessionalSearch value={query} onChange={setQuery} />
        <ProfessionalFilters value={filters} onChange={setFilters} />
      </div>
      <ProfessionalGrid
        professionals={professionals}
        total={total}
        isLoading={isLoading}
        detailsPathFor={customerRoutes.professionalDetails}
      />
      <div>
        <h2 className="mb-3 text-sm font-medium text-ink-soft">Near you</h2>
        <NearbyProfessionals detailsPathFor={customerRoutes.professionalDetails} />
      </div>
    </div>
  );
}

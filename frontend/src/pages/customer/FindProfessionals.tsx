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
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    setPage(1);
  }, [query, filters]);

  useEffect(() => {
    let active = true;
    setError("");
    setIsLoading(true);
    professionalsApi
      .list({ query: query.trim() || undefined, professionalType: filters.professionalType, page, pageSize: 20 })
      .then((response) => {
        if (!active) return;
        setProfessionals(response.items);
        setTotal(response.total);
      })
      .catch(() => { if (active) setError("Could not load professionals. Please try again."); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [query, filters, page]);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Find a professional</h1>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ProfessionalSearch value={query} onChange={setQuery} />
        <ProfessionalFilters value={filters} onChange={setFilters} />
      </div>
      {error && <p role="alert">{error}</p>}
      {!isLoading && !error && <p className="text-sm text-ink-soft" role="status">{total} professional{total === 1 ? "" : "s"} available to browse</p>}
      <ProfessionalGrid
        key={`${query}-${filters.professionalType ?? "all"}`}
        pageSize={20}
        onPageChange={setPage}
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

import { useEffect, useState } from "react";
import { professionalsApi } from "@/api/professionals.api";
import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import { ProfessionalSearch } from "@/components/professionals/ProfessionalSearch";
import { ProfessionalFilters, type ProfessionalFiltersValue } from "@/components/professionals/ProfessionalFilters";
import { publicRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";

export default function FindTailor() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<ProfessionalFiltersValue>({ professionalType: "tailor", radiusKm: 10 });
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    professionalsApi
      .list({ professionalType: "tailor", query })
      .then((response) => {
        setProfessionals(response.items);
        setTotal(response.total);
      })
      .finally(() => setIsLoading(false));
  }, [query]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl text-ink">Find a tailor</h1>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <ProfessionalSearch value={query} onChange={setQuery} />
        <ProfessionalFilters value={filters} onChange={setFilters} />
      </div>
      <ProfessionalGrid professionals={professionals} total={total} isLoading={isLoading} detailsPathFor={publicRoutes.professionalProfile} />
    </div>
  );
}

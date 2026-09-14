import { useEffect, useState } from "react";
import { professionalsApi } from "@/api/professionals.api";
import { ProfessionalGrid } from "@/components/professionals/ProfessionalGrid";
import { ProfessionalSearch } from "@/components/professionals/ProfessionalSearch";
import { publicRoutes } from "@/config/routes.config";
import type { Professional } from "@/types/professional";

export default function FindDesigner() {
  const [query, setQuery] = useState("");
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    professionalsApi
      .list({ professionalType: "designer", query })
      .then((response) => {
        setProfessionals(response.items);
        setTotal(response.total);
      })
      .finally(() => setIsLoading(false));
  }, [query]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="mb-6 font-display text-2xl text-ink">Find a designer</h1>
      <div className="mb-6"><ProfessionalSearch value={query} onChange={setQuery} /></div>
      <ProfessionalGrid professionals={professionals} total={total} isLoading={isLoading} detailsPathFor={publicRoutes.professionalProfile} />
    </div>
  );
}

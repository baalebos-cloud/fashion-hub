import { Select } from "@/components/ui/select";
import type { ProfessionalType } from "@/types/professional";

export interface ProfessionalFiltersValue {
  professionalType?: ProfessionalType;
  radiusKm: number;
}

export function ProfessionalFilters({ value, onChange }: { value: ProfessionalFiltersValue; onChange: (v: ProfessionalFiltersValue) => void }) {
  return (
    <div className="flex flex-wrap gap-3">
      <Select
        value={value.professionalType ?? ""}
        onChange={(e) => onChange({ ...value, professionalType: (e.target.value || undefined) as ProfessionalType | undefined })}
        className="w-auto"
      >
        <option value="">All types</option>
        <option value="tailor">Tailors</option>
        <option value="designer">Designers</option>
      </Select>
      <Select value={value.radiusKm} onChange={(e) => onChange({ ...value, radiusKm: Number(e.target.value) })} className="w-auto">
        <option value={5}>Within 5 km</option>
        <option value={10}>Within 10 km</option>
        <option value={25}>Within 25 km</option>
        <option value={50}>Within 50 km</option>
      </Select>
    </div>
  );
}

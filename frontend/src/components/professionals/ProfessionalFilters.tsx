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
    </div>
  );
}

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { MeasurementGuide } from "./MeasurementGuide";
import { SaveMeasurementProfile } from "./SaveMeasurementProfile";
import { STANDARD_MEASUREMENT_FIELDS } from "@/components/designs/MeasurementFieldSelector";
import { useMeasurements } from "@/hooks/use-measurements";
import type { MeasurementField } from "@/types/measurement";

export interface MeasurementFormProps {
  onSaved?: () => void;
  /** When a design specifies required_measurement_fields (see
   * backend/docs/measurement-requirements.md), pass them here to narrow
   * the form to just what that tailor/designer asked for. Omitted or
   * empty falls back to the full standard set -- "or client filled it
   * themselves" is the default, not a special case. */
  requiredFields?: string[];
}

export function MeasurementForm({ onSaved, requiredFields }: MeasurementFormProps) {
  const { createProfile } = useMeasurements();
  const fieldNames = requiredFields && requiredFields.length > 0 ? requiredFields : STANDARD_MEASUREMENT_FIELDS;
  const [values, setValues] = useState<Record<string, string>>({});
  const [unit, setUnit] = useState("cm");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave(label: string) {
    setIsSaving(true);
    try {
      const fields: MeasurementField[] = fieldNames.filter((name) => values[name]).map((name) => ({
        field_name: name,
        value: Number(values[name]),
        unit,
      }));
      await createProfile(label, undefined, fields);
      onSaved?.();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-ink-soft">
          {requiredFields && requiredFields.length > 0 ? "Measurements needed for this design" : "Enter measurements"}
        </h2>
        <Select value={unit} onChange={(e) => setUnit(e.target.value)} className="w-24">
          <option value="cm">cm</option>
          <option value="in">in</option>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {fieldNames.map((name) => (
          <div key={name}>
            <label className="mb-1 block text-xs capitalize text-ink-soft">{name.replace(/_/g, " ")}</label>
            <Input
              type="number"
              value={values[name] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
            />
          </div>
        ))}
      </div>

      <MeasurementGuide />
      <SaveMeasurementProfile onSave={handleSave} isSaving={isSaving} />
    </div>
  );
}

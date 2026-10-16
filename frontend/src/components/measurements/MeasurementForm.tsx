import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useState, useId } from "react";
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
  const fieldId = useId();
  const [error, setError] = useState<string | null>(null);
  const { createProfile } = useMeasurements();
  const fieldNames = requiredFields && requiredFields.length > 0 ? requiredFields : STANDARD_MEASUREMENT_FIELDS;
  const [values, setValues] = useState<Record<string, string>>({});
  const [unit, setUnit] = useState("cm");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave(label: string) {
    setIsSaving(true);
    setError(null);
    try {
      const fields: MeasurementField[] = fieldNames.filter((name) => values[name]).map((name) => ({
        field_name: name,
        value: Number(values[name]),
        unit,
      }));
      await createProfile(label, undefined, fields);
      onSaved?.();
    } catch (err) {
      setError(getDisplayErrorMessage(err));
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
        <Select aria-label="Measurement unit" value={unit} onChange={(e) => setUnit(e.target.value)} className="w-24">
          <option value="cm">cm</option>
          <option value="in">in</option>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {fieldNames.map((name) => (
          <div key={name}>
            <label htmlFor={`${fieldId}-${name}`} className="mb-1 block text-xs capitalize text-ink-soft">{name.replace(/_/g, " ")}</label>
            <Input
              id={`${fieldId}-${name}`}
              type="number" min="0.01" max="9999.99" step="0.01"
              value={values[name] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [name]: e.target.value }))}
            />
          </div>
        ))}
      </div>

      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      <MeasurementGuide />
      <SaveMeasurementProfile onSave={handleSave} isSaving={isSaving} />
    </div>
  );
}

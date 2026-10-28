import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { useState, useId } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { MeasurementGuide } from "./MeasurementGuide";
import { SaveMeasurementProfile } from "./SaveMeasurementProfile";
import { STANDARD_MEASUREMENT_FIELDS } from "@/components/designs/MeasurementFieldSelector";
import { useMeasurements } from "@/hooks/use-measurements";
import { validateMeasurementFields, type MeasurementUnit } from "@/lib/measurements/validation";

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
  const [unit, setUnit] = useState<MeasurementUnit>("cm");
  const [step, setStep] = useState<"measure" | "review">("measure");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  async function handleSave(label: string) {
    setIsSaving(true);
    setError(null);
    try {
      const { fields, errors } = validateMeasurementFields(fieldNames, values, unit);
      setFieldErrors(errors);
      if (Object.keys(errors).length > 0) {
        setError("Correct the highlighted measurements before saving.");
        setStep("measure");
        return;
      }
      if (step !== "review") {
        setStep("review");
        return;
      }
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
        <Select aria-label="Measurement unit" value={unit} onChange={(e) => { setUnit(e.target.value as MeasurementUnit); setStep("measure"); }} className="w-24">
          <option value="cm">cm</option>
          <option value="in">in</option>
        </Select>
      </div>

      <p className="text-xs text-ink-soft" aria-live="polite">Step {step === "measure" ? "1 of 2: Enter measurements" : "2 of 2: Review before saving"}</p>
      <div className="grid grid-cols-2 gap-3">
        {fieldNames.map((name) => (
          <div key={name}>
            <label htmlFor={`${fieldId}-${name}`} className="mb-1 block text-xs capitalize text-ink-soft">{name.replace(/_/g, " ")}</label>
            <Input
              id={`${fieldId}-${name}`}
              type="number" min="0.01" max="9999.99" step="0.01"
              value={values[name] ?? ""}
              onChange={(e) => { setValues((prev) => ({ ...prev, [name]: e.target.value })); setFieldErrors((prev) => ({ ...prev, [name]: "" })); setStep("measure"); }}
              aria-invalid={Boolean(fieldErrors[name])}
            />
            {fieldErrors[name] && <p role="alert" className="text-xs text-thread">{fieldErrors[name]}</p>}
          </div>
        ))}
      </div>

      {error && <p role="alert" className="text-sm text-thread">{error}</p>}
      {step === "review" && <p role="status" className="text-sm text-ink-soft">Confirm these measurements and your profile name before saving. Edit any field to return to step one.</p>}
      <MeasurementGuide />
      <SaveMeasurementProfile onSave={handleSave} isSaving={isSaving} />
    </div>
  );
}

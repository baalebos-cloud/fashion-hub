import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/hooks/use-auth";
import { useMeasurements } from "@/hooks/use-measurements";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MeasurementGuide } from "./MeasurementGuide";
import {
  measurementSchema, measurementNames, measurementFieldsInCentimetres,
  type MeasurementInput,
} from "@/schemas/measurement";

const DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const defaultInput: MeasurementInput = { label: "", unit: "cm", values: {} };

export interface MeasurementWorkflowProps {
  onSaved?: () => void;
  requiredFields?: string[];
}

/** Saves per-user drafts on this device. No draft is sent to a server until confirmed. */
export function MeasurementWorkflow({ onSaved, requiredFields }: MeasurementWorkflowProps) {
  const { user } = useAuth();
  const { createProfile, isSaving } = useMeasurements();
  const [step, setStep] = useState<"measure" | "review">("measure");
  const [isRestored, setIsRestored] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const draftKey = user?.id ? `seam:measurements:draft:${user.id}` : null;
  const names = requiredFields?.length
    ? measurementNames.filter((name) => requiredFields.includes(name))
    : [...measurementNames];
  const unsupported = requiredFields?.filter((name) => !measurementNames.some((field) => field === name)) ?? [];

  const { control, register, reset, getValues, setValue, trigger, handleSubmit, formState: { errors } } =
    useForm<MeasurementInput>({
      resolver: zodResolver(measurementSchema),
      defaultValues: defaultInput,
      mode: "onBlur",
    });
  const input = useWatch({ control });
  const selectedUnit = input.unit ?? "cm";

  useEffect(() => {
    if (!draftKey) return;
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const saved: unknown = JSON.parse(raw);
        if (saved && typeof saved === "object" && "timestamp" in saved && "data" in saved) {
          const item = saved as { timestamp: number; data: unknown };
          if (Number.isFinite(item.timestamp) && Date.now() - item.timestamp < DRAFT_TTL_MS) {
            const parsed = measurementSchema.safeParse(item.data);
            if (parsed.success) reset(parsed.data);
          }
        }
      }
    } catch { /* Storage can be denied or invalid; keep form usable. */ }
    setIsRestored(true);
  }, [draftKey, reset]);

  useEffect(() => {
    if (!draftKey || !isRestored) return;
    try { localStorage.setItem(draftKey, JSON.stringify({ timestamp: Date.now(), data: input })); }
    catch { /* Storage may be disabled. */ }
  }, [draftKey, input, isRestored]);

  function changeUnit(unit: "cm" | "in") {
    const current = getValues("unit");
    if (unit === current) return;
    for (const name of measurementNames) {
      const value = getValues(`values.${name}`);
      if (typeof value === "number" && Number.isFinite(value)) {
        setValue(`values.${name}`, Math.round((unit === "in" ? value / 2.54 : value * 2.54) * 100) / 100);
      }
    }
    setValue("unit", unit);
    setStep("measure");
  }

  async function review() {
    setServerError(null);
    if (unsupported.length) {
      setServerError("This design requests unsupported measurement fields. Contact the tailor.");
      return;
    }
    const valid = await trigger();
    if (!valid) return;
    const values = getValues("values");
    if (names.some((name) => values[name] === undefined)) {
      setServerError("Complete all the measurements required for this design.");
      return;
    }
    setStep("review");
  }

  const submit = handleSubmit(async (value) => {
    if (step !== "review") return;
    setServerError(null);
    try {
      await createProfile(value.label, undefined, measurementFieldsInCentimetres(value));
      if (draftKey) { try { localStorage.removeItem(draftKey); } catch { /* no-op */ } }
      reset(defaultInput);
      setStep("measure");
      onSaved?.();
    } catch (err) {
      setServerError(getDisplayErrorMessage(err));
    }
  });

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <p className="text-sm text-ink-soft" aria-live="polite">
        Step {step === "measure" ? "1 of 2: Enter your measurements" : "2 of 2: Review and confirm"}
      </p>
      <label className="text-sm text-ink">
        Measurement profile name
        <Input {...register("label")} maxLength={128} placeholder="My measurements" aria-invalid={Boolean(errors.label)} />
        {errors.label && <span role="alert">{errors.label.message}</span>}
      </label>
      <label className="text-sm text-ink">
        Unit
        <select value={selectedUnit} onChange={(e) => changeUnit(e.target.value === "in" ? "in" : "cm")} aria-label="Measurement unit" className="w-full rounded-lg border border-line p-2">
          <option value="cm">Centimetres</option>
          <option value="in">Inches</option>
        </select>
      </label>
      <div className="grid grid-cols-2 gap-3">
        {names.map((name) => (
          <label key={name} className="text-sm capitalize text-ink">
            {name.replace(/_/g, " ")}
            <Input type="number" step="0.01" min="0.01" max={selectedUnit === "in" ? "393.7" : "999.99"}
              {...register(`values.${name}`, {
                setValueAs: (value: string) => value === "" ? undefined : Number(value),
              })}
              onInput={() => setStep("measure")}
              aria-invalid={Boolean(errors.values?.[name])} />
            {errors.values?.[name] && <span role="alert" className="text-xs text-thread">{errors.values[name]?.message}</span>}
          </label>
        ))}
      </div>
      <MeasurementGuide />
      {step === "review" && (
        <p role="status" className="text-sm">Please verify the measurement values and unit above. Measurements are saved to your profile in centimetres.</p>
      )}
      {serverError && <p role="alert" className="text-sm text-thread">{serverError}</p>}
      <div className="flex gap-2">
        {step === "review" ? (
          <>
            <Button type="button" variant="secondary" onClick={() => setStep("measure")}>Edit measurements</Button>
            <Button type="submit" disabled={isSaving} isLoading={isSaving}>Confirm and save</Button>
          </>
        ) : (
          <Button type="button" onClick={() => void review()}>Review measurements</Button>
        )}
      </div>
    </form>
  );
}

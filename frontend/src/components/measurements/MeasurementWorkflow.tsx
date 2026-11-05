import { useEffect, useState } from "react";
import { MEASUREMENT_DRAFT_PREFIX } from "@/lib/auth/account-isolation";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuth } from "@/hooks/use-auth";
import { useMeasurements } from "@/hooks/use-measurements";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MeasurementGuide } from "./MeasurementGuide";
import { MeasurementScanner, type AppliedSuggestions } from "./MeasurementScanner";
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
  /** Fields filled from photos, flagged until the customer edits them. */
  const [photoSources, setPhotoSources] = useState<AppliedSuggestions>({});
  const draftKey = user?.id ? `${MEASUREMENT_DRAFT_PREFIX}${user.id}` : null;
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
      setPhotoSources({});
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
      <MeasurementScanner onApply={(fields) => {
        // Suggestions arrive in centimetres; switch the form to cm first so nothing is misread.
        changeUnit("cm");
        const applied: AppliedSuggestions = {};
        for (const name of names) {
          const suggestion = fields[name];
          if (!suggestion) continue;
          setValue(`values.${name}`, suggestion.value, { shouldValidate: true });
          applied[name] = suggestion;
        }
        setPhotoSources(applied);
        setStep("measure");
      }} />
      <div className="grid grid-cols-2 gap-3">
        {names.map((name) => (
          <label key={name} className="text-sm capitalize text-ink">
            {name.replace(/_/g, " ")}
            <Input type="number" step="0.01" min="0.01" max={selectedUnit === "in" ? "393.7" : "999.99"}
              {...register(`values.${name}`, {
                setValueAs: (value: string) => value === "" ? undefined : Number(value),
              })}
              onInput={() => {
                setStep("measure");
                setPhotoSources((all) => { const next = { ...all }; delete next[name]; return next; });
              }}
              aria-invalid={Boolean(errors.values?.[name])} />
            {photoSources[name] && (
              <span className="text-[11px] normal-case text-[#8a5f1f]">
                {photoSources[name]?.source === "tape" ? "From your tape photo, please confirm" : "Photo estimate, please confirm"}
              </span>
            )}
            {errors.values?.[name] && <span role="alert" className="text-xs text-thread">{errors.values[name]?.message}</span>}
          </label>
        ))}
      </div>
      <MeasurementGuide />
      {step === "review" && (
        <p role="status" className="text-sm">Please verify the measurement values and unit above. Measurements are saved to your profile in centimetres.
          {Object.keys(photoSources).length > 0 && " Values from photos are drafts until you confirm them here."}</p>
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

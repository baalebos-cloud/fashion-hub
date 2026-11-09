import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { aiService, type MeasurementFieldName, type MeasurementSuggestion, type PhotoMeasurementDraft } from "@/services/aiService";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { prepareImage } from "@/lib/media/prepare-image";
import { PHOTO_ACCEPT, validateImageFile } from "@/lib/utils/image";

const MAX_TAPE_PHOTOS = 4;
// Any phone photo (incl. iPhone HEIC); each is resized to a JPEG before it is sent.
const ACCEPT = PHOTO_ACCEPT;

const FIELD_LABELS: Record<MeasurementFieldName, string> = {
  chest: "Chest", waist: "Waist", hip: "Hip", inseam: "Inseam",
  shoulder_width: "Shoulder width", sleeve_length: "Sleeve length", neck: "Neck",
};

/** Values applied to the form (centimetres) plus where each came from, so the form can flag them. */
export type AppliedSuggestions = Partial<Record<MeasurementFieldName, { value: number; source: "tape" | "estimate" }>>;

interface Props {
  onApply: (fields: AppliedSuggestions) => void;
  garmentType?: string;
}

function usePreview(file: File | null) {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  return url;
}

function Thumb({ file, label, onRemove }: { file: File; label: string; onRemove: () => void }) {
  const url = usePreview(file);
  return (
    <div className="relative w-fit">
      {url && <img src={url} alt={label} className="h-24 w-20 rounded-lg border border-line object-cover" />}
      <button type="button" onClick={onRemove} aria-label={`Remove ${label}`}
        className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-ink text-xs text-paper">
        ×
      </button>
    </div>
  );
}

function SourceTag({ suggestion }: { suggestion: MeasurementSuggestion }) {
  const pct = Math.round(suggestion.confidence * 100);
  return suggestion.source === "tape"
    ? <span className="rounded-full bg-[#e5f3ea] px-2 py-0.5 text-[11px] font-medium text-[#256a3f]">Read from your photo · {pct}%</span>
    : <span className="rounded-full bg-[#fbf0dd] px-2 py-0.5 text-[11px] font-medium text-[#8a5f1f]">Estimate · {pct}%</span>;
}

/** Checks the photo, then resizes it to a JPEG for analysis. Throws a message to show on failure. */
async function readyPhoto(file: File): Promise<File> {
  const problem = validateImageFile(file);
  if (problem) throw new Error(problem);
  return prepareImage(file);
}

/**
 * Photo measurement assistant. The customer uploads a full-body photo (with
 * their height, for scale) and/or close-ups of a tape measure; Tailora drafts
 * the form; the customer edits each value and confirms before it is applied.
 * Nothing is saved here: saving happens in the form's own review step.
 */
export function MeasurementScanner({ onApply, garmentType }: Props) {
  const [bodyPhoto, setBodyPhoto] = useState<File | null>(null);
  const [tapePhotos, setTapePhotos] = useState<File[]>([]);
  const [height, setHeight] = useState("");
  const [draft, setDraft] = useState<PhotoMeasurementDraft | null>(null);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const heightCm = height.trim() === "" ? null : Number(height);
  const heightInvalid = heightCm !== null && (!Number.isFinite(heightCm) || heightCm < 100 || heightCm > 230);
  const canAnalyse = (bodyPhoto || tapePhotos.length > 0) && !heightInvalid && !busy && !preparing;

  function resetResult() { setDraft(null); setChecked(false); }

  async function pickBody(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setPreparing(true);
    try {
      setBodyPhoto(await readyPhoto(file));
      resetResult();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "This photo couldn't be used. Try another one."));
    } finally {
      setPreparing(false);
    }
  }

  async function pickTape(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!files.length) return;
    const room = MAX_TAPE_PHOTOS - tapePhotos.length;
    setError(null);
    setPreparing(true);
    try {
      const ready: File[] = [];
      for (const file of files.slice(0, room)) ready.push(await readyPhoto(file));
      setTapePhotos((all) => [...all, ...ready].slice(0, MAX_TAPE_PHOTOS));
      if (files.length > room) setError(`Up to ${MAX_TAPE_PHOTOS} photos here; extra photos were left out.`);
      resetResult();
    } catch (err) {
      setError(getDisplayErrorMessage(err, "This photo couldn't be used. Try another one."));
    } finally {
      setPreparing(false);
    }
  }

  async function analyse() {
    if (!canAnalyse) return;
    setBusy(true);
    setError(null);
    resetResult();
    try {
      const result = await aiService.analyzeMeasurementPhotos({ bodyPhoto, tapePhotos, heightCm, garmentType });
      setDraft(result);
      setEdited(Object.fromEntries(result.fields.map((f) => [f.field_name, String(f.value)])));
      if (!result.fields.length) setError("Tailora couldn't read any measurements from these photos. See the tips below and try again.");
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Photo analysis is unavailable right now. Enter your measurements manually."));
    } finally {
      setBusy(false);
    }
  }

  function apply() {
    if (!draft) return;
    const applied: AppliedSuggestions = {};
    for (const suggestion of draft.fields) {
      const raw = (edited[suggestion.field_name] ?? "").trim();
      if (!raw) continue;
      const value = Number(raw);
      if (!Number.isFinite(value) || value <= 0 || value > 300) {
        setError(`Check ${FIELD_LABELS[suggestion.field_name].toLowerCase()}: enter a value between 1 and 300 cm.`);
        return;
      }
      applied[suggestion.field_name] = { value: Math.round(value * 10) / 10, source: suggestion.source };
    }
    if (!Object.keys(applied).length) { setError("There are no values to apply."); return; }
    onApply(applied);
    setDraft(null);
    setChecked(false);
    setError(null);
  }

  return (
    <section className="rounded-card border border-line bg-paper p-4 sm:p-5" aria-label="Measure with photos">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-lg text-ink">Measure with photos</h3>
        <span className="text-xs text-ink-soft">Optional · photos are not stored</span>
      </div>
      <p className="mt-1 text-sm text-ink-soft">
        Know your measurements? Add a photo of them and Tailora reads them for you. Not sure? Add a full-body
        photo with your height and Tailora estimates them. You check and edit every value before anything is saved.
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-ink">1. Full-body photo</span>
          <ul className="list-disc pl-5 text-xs text-ink-soft">
            <li>Fitted clothes, standing straight, facing the camera</li>
            <li>Head to feet in the frame, arms slightly away from your body</li>
          </ul>
          {bodyPhoto
            ? <Thumb file={bodyPhoto} label="Full-body photo" onRemove={() => { setBodyPhoto(null); resetResult(); }} />
            : (
              <label className="flex h-24 cursor-pointer items-center justify-center rounded-lg border border-dashed border-line text-sm text-ink-soft hover:border-brass">
                Add full-body photo
                <input type="file" accept={ACCEPT} className="sr-only" aria-label="Full-body photo" onChange={(e) => void pickBody(e)} />
              </label>
            )}
          <label className="text-sm text-ink">
            Your height (cm)
            <input type="number" inputMode="decimal" min={100} max={230} value={height}
              onChange={(e) => { setHeight(e.target.value); resetResult(); }} placeholder="e.g. 172"
              aria-invalid={heightInvalid} aria-describedby="height-help"
              className="mt-1 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm focus:border-brass focus:outline-none" />
          </label>
          <p id="height-help" className={heightInvalid ? "text-xs text-thread" : "text-xs text-ink-soft"}>
            {heightInvalid ? "Enter a height between 100 and 230 cm." : "Your height gives the photo a real-world scale. Without it, only tape readings are used."}
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-ink">2. Your measurements in a photo <span className="font-normal text-ink-soft">(most accurate)</span></span>
          <p className="text-xs text-ink-soft">
            Already measured? Add a photo of them written down (a tailor's card or a note). Or close-ups of a
            tape measure where the number is readable, e.g. around your chest, waist or neck.
          </p>
          <div className="flex flex-wrap gap-3">
            {tapePhotos.map((file, index) => (
              <Thumb key={`${file.name}-${index}`} file={file} label={`Measurement photo ${index + 1}`}
                onRemove={() => { setTapePhotos((all) => all.filter((_, i) => i !== index)); resetResult(); }} />
            ))}
            {tapePhotos.length < MAX_TAPE_PHOTOS && (
              <label className="flex h-24 w-20 cursor-pointer items-center justify-center rounded-lg border border-dashed border-line text-center text-xs text-ink-soft hover:border-brass">
                + Add
                <input type="file" accept={ACCEPT} multiple className="sr-only" aria-label="Measurement photos" onChange={(e) => void pickTape(e)} />
              </label>
            )}
          </div>
        </div>
      </div>

      {preparing && <p role="status" className="mt-3 text-xs text-ink-soft">Preparing your photo…</p>}
      <Button type="button" className="mt-4 w-full sm:w-auto" onClick={() => void analyse()} disabled={!canAnalyse} isLoading={busy}>
        {busy ? "Analysing your photos…" : "Analyse photos"}
      </Button>
      {bodyPhoto && !heightCm && !tapePhotos.length && !busy && (
        <p className="mt-2 text-xs text-ink-soft">Add your height, or a photo of your measurements, so Tailora can measure.</p>
      )}

      {draft && draft.fields.length > 0 && (
        <div className="mt-5 border-t border-line pt-4" aria-live="polite">
          <h4 className="text-sm font-medium text-ink">Check your draft (cm)</h4>
          <p className="mt-1 text-xs text-ink-soft">{draft.notes}</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {draft.fields.map((suggestion) => (
              <label key={suggestion.field_name} className="flex flex-col gap-1 text-sm text-ink">
                <span className="flex items-center justify-between gap-2">
                  {FIELD_LABELS[suggestion.field_name]}
                  <SourceTag suggestion={suggestion} />
                </span>
                <input type="number" step="0.1" min="1" max="300" inputMode="decimal"
                  value={edited[suggestion.field_name] ?? ""} aria-label={`${FIELD_LABELS[suggestion.field_name]} in centimetres`}
                  onChange={(e) => { setEdited((all) => ({ ...all, [suggestion.field_name]: e.target.value })); setChecked(false); }}
                  className="w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm focus:border-brass focus:outline-none" />
              </label>
            ))}
          </div>
          {draft.photo_issues.length > 0 && (
            <div className="mt-3 rounded-lg bg-muslin p-3 text-xs text-ink-soft">
              <p className="font-medium text-ink">For better accuracy</p>
              <ul className="mt-1 list-disc pl-4">{draft.photo_issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
            </div>
          )}
          <label className="mt-4 flex items-start gap-2 text-sm text-ink">
            <input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} className="mt-0.5" />
            I've checked these values. Estimates can be off by a few centimetres.
          </label>
          <Button type="button" className="mt-3 w-full sm:w-auto" disabled={!checked} onClick={apply}>
            Use these in my form
          </Button>
        </div>
      )}
      {error && <p role="alert" className="mt-3 text-sm text-thread">{error}</p>}
    </section>
  );
}

import { useState } from "react";
import { aiService, type SuggestedMeasurements } from "@/services/aiService";
import { Button } from "@/components/ui/button";

interface Props {
  onApply: (fields: { chest?: number; waist?: number; hip?: number }) => void;
}

export function MeasurementScanner({ onApply }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<SuggestedMeasurements | null>(null);
  const [edited, setEdited] = useState<{ chest: string; waist: string; hip: string }>({
    chest: "", waist: "", hip: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyse() {
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const data = await aiService.extractMeasurements(file);
      setResult(data);
      setEdited({
        chest: data.bust == null ? "" : String(data.bust),
        waist: data.waist == null ? "" : String(data.waist),
        hip: data.hips == null ? "" : String(data.hips),
      });
    } catch {
      setError("AI analysis is unavailable. Enter measurements manually.");
    } finally {
      setBusy(false);
    }
  }

  function apply() {
    if (!result) return;
    const values: { chest?: number; waist?: number; hip?: number } = {};
    for (const name of ["chest", "waist", "hip"] as const) {
      const raw = edited[name].trim();
      if (!raw) continue;
      const value = Number(raw);
      const centimetres = result.unit === "in" ? value * 2.54 : value;
      if (!Number.isFinite(centimetres) || centimetres <= 0 || centimetres > 300) {
        setError("Enter positive, realistic measurements before applying.");
        return;
      }
      values[name] = Math.round(centimetres * 100) / 100;
    }
    if (!Object.keys(values).length) {
      setError("AI could not read a reliable measurement. Use a measuring tape.");
      return;
    }
    onApply(values);
    setResult(null);
    setFile(null);
  }

  return (
    <section className="rounded-lg border border-line p-4" aria-label="Optional AI measurement assistant">
      <h3 className="font-medium">Photo measurement assistant (optional)</h3>
      <p className="text-sm text-ink-soft">
        Only upload a photo you have permission to use. Photos cannot reliably determine body size;
        place a readable measuring tape in the picture. No measurement is saved without confirmation.
      </p>
      <input aria-label="Fitting photo" type="file" accept="image/jpeg,image/png,image/webp"
        onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null); }}
      />
      <Button type="button" onClick={() => void analyse()} disabled={!file || busy}>
        {busy ? "Analysing…" : "Analyse photo"}
      </Button>
      {result && (
        <div className="flex flex-col gap-2" aria-live="polite">
          <p className="text-sm">{result.notes}</p>
          <p className="text-sm">Confidence: {Math.round(result.confidence * 100)}%.
            These are unverified suggestions. Compare each value with a measuring tape.
          </p>
          {(["chest", "waist", "hip"] as const).map((name) => (
            <label key={name} className="text-sm capitalize">
              {name} ({result.unit})
              <input className="block w-full rounded border p-2" type="number" min="0.01" step="0.01"
                value={edited[name]} onChange={(event) => setEdited((previous) => ({ ...previous, [name]: event.target.value }))} />
            </label>
          ))}
          <Button type="button" onClick={apply}>I have checked these measurements. Apply to form</Button>
        </div>
      )}
      {error && <p role="alert" className="text-sm">{error}</p>}
    </section>
  );
}

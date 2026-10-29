import { useState } from "react";
import { extractMeasurementEstimate, type MeasurementEstimate } from "../services/aiService";

type Props = {
  accessToken: string;
  onConfirm: (measurements: MeasurementEstimate) => void;
};

/** Advisory-only. Does not save measurements until the customer confirms. */
export function MeasurementScanner({ accessToken, onConfirm }: Props) {
  const [value, setValue] = useState<MeasurementEstimate | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function scan(file: File) {
    setBusy(true);
    setError("");
    try {
      setValue(await extractMeasurementEstimate(file, accessToken));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to analyze photo");
    } finally {
      setBusy(false);
    }
  }
  function update(key: "bust" | "waist" | "hips" | "inseam", raw: string) {
    setValue(current => current ? { ...current, [key]: raw === "" ? null : Number(raw) } : current);
  }
  const valid = value && ["bust", "waist", "hips", "inseam"].every(key => {
    const n = value[key as keyof MeasurementEstimate];
    return n === null || (typeof n === "number" && Number.isFinite(n) && n > 0 && n <= 300);
  });
  return <section aria-label="Measurement scanner">
    <p>AI suggestions are estimates only. Confirm measurements using a measuring tape.</p>
    <label>Fitting photo
      <input type="file" accept="image/jpeg,image/png" disabled={busy}
        onChange={e => { const file = e.target.files?.[0]; if (file) void scan(file); }} />
    </label>
    {busy && <p role="status">Analyzing image…</p>}
    {error && <p role="alert">{error}</p>}
    {value && <>
      <label>Units
        <select value={value.unit} onChange={e => { const unit = e.target.value as "cm" | "inches"; const scale = unit === value.unit ? 1 : unit === "cm" ? 2.54 : 1 / 2.54; setValue({ ...value, unit, bust: value.bust === null ? null : +(value.bust * scale).toFixed(2), waist: value.waist === null ? null : +(value.waist * scale).toFixed(2), hips: value.hips === null ? null : +(value.hips * scale).toFixed(2), inseam: value.inseam === null ? null : +(value.inseam * scale).toFixed(2) }); }}>
          <option value="cm">cm</option><option value="inches">inches</option>
        </select>
      </label>
      {(["bust", "waist", "hips", "inseam"] as const).map(key => <label key={key}>
        {key}<input type="number" min="0.01" max="300" step="0.1"
          value={value[key] ?? ""} onChange={e => update(key, e.target.value)} />
      </label>)}
      <button disabled={!valid} onClick={() => { if (valid) onConfirm(value); }}>
        Confirm measurements
      </button>
    </>}
  </section>;
}

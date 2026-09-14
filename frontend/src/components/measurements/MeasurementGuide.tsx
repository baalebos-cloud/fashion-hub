const GUIDE_STEPS = [
  { field: "Chest", tip: "Measure around the fullest part of your chest, keeping the tape level." },
  { field: "Waist", tip: "Measure around your natural waistline, above your belly button." },
  { field: "Hip", tip: "Measure around the fullest part of your hips." },
  { field: "Sleeve length", tip: "From shoulder seam to wrist, with arm slightly bent." },
  { field: "Inseam", tip: "From the crotch to the bottom of the ankle." },
];

export function MeasurementGuide() {
  return (
    <div className="flex flex-col gap-3 rounded-card border border-line p-4">
      <h3 className="text-sm font-medium text-ink">How to measure</h3>
      {GUIDE_STEPS.map((step) => (
        <div key={step.field} className="text-sm">
          <span className="font-medium text-ink">{step.field}: </span>
          <span className="text-ink-soft">{step.tip}</span>
        </div>
      ))}
    </div>
  );
}

export function ReviewSummary({ average, count }: { average: number; count: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-lg font-medium text-ink">★ {average.toFixed(1)}</span>
      <span className="text-sm text-ink-soft">({count} review{count === 1 ? "" : "s"})</span>
    </div>
  );
}

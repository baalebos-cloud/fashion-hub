export function ProductQuantitySelector({ quantity, max, onChange }: { quantity: number; max: number; onChange: (quantity: number) => void }) {
  return (
    <div className="inline-flex items-center rounded-lg border border-line">
      <button
        type="button"
        onClick={() => onChange(Math.max(1, quantity - 1))}
        className="flex h-9 w-9 items-center justify-center text-ink hover:bg-muslin"
        aria-label="Decrease quantity"
      >
        −
      </button>
      <span className="w-10 text-center text-sm text-ink">{quantity}</span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, quantity + 1))}
        disabled={quantity >= max}
        className="flex h-9 w-9 items-center justify-center text-ink hover:bg-muslin disabled:opacity-40"
        aria-label="Increase quantity"
      >
        +
      </button>
    </div>
  );
}

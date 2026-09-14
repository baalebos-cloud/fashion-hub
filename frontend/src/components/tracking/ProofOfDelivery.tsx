export function ProofOfDelivery({ imageUrl }: { imageUrl?: string | null }) {
  if (!imageUrl) return null;
  return (
    <div>
      <div className="mb-2 text-sm font-medium text-ink">Proof of delivery</div>
      <img src={imageUrl} alt="Proof of delivery" className="w-full max-w-xs rounded-card border border-line" />
    </div>
  );
}

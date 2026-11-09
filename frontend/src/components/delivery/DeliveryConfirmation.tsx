import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadFile } from "@/lib/storage/file-storage";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function DeliveryConfirmation({ onConfirm }: { onConfirm: (proofOfDeliveryUrl?: string) => Promise<void> }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePhotoChange() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const { url } = await uploadFile("/deliveries/proof", file);
      setPhotoUrl(url);
    } catch (failure) {
      setError(getDisplayErrorMessage(failure, "The photo couldn't be uploaded. Try again."));
    } finally {
      setUploading(false);
    }
  }

  async function handleConfirm() {
    setIsSubmitting(true);
    try {
      await onConfirm(photoUrl ?? undefined);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <input ref={fileInputRef} type="file" accept="image/*" capture="environment" onChange={() => void handlePhotoChange()} className="text-sm" />
      {uploading && <p role="status" className="text-xs text-ink-soft">Uploading photo…</p>}
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
      {photoUrl && <img src={photoUrl} alt="Proof of delivery" className="h-32 w-32 rounded-card object-cover" />}
      <Button onClick={handleConfirm} isLoading={isSubmitting} disabled={uploading} className="self-start">Confirm delivered</Button>
    </div>
  );
}

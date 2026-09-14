import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadFile } from "@/lib/storage/file-storage";

export function DeliveryConfirmation({ onConfirm }: { onConfirm: (proofOfDeliveryUrl?: string) => Promise<void> }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  async function handlePhotoChange() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    const { url } = await uploadFile("/deliveries/proof", file);
    setPhotoUrl(url);
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
      <input ref={fileInputRef} type="file" accept="image/*" capture="environment" onChange={handlePhotoChange} className="text-sm" />
      {photoUrl && <img src={photoUrl} alt="Proof of delivery" className="h-32 w-32 rounded-card object-cover" />}
      <Button onClick={handleConfirm} isLoading={isSubmitting} className="self-start">Confirm delivered</Button>
    </div>
  );
}

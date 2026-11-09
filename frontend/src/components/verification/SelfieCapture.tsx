import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { uploadFile } from "@/lib/storage/file-storage";
import { prepareImage } from "@/lib/media/prepare-image";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

/**
 * A selfie taken now with the front camera (phones open the camera straight away). Tailora compares it,
 * and the profile photo, with the photo on the NIN record, so nobody can verify with someone else's
 * NIN or show someone else's face. Uploaded privately, like the ID document.
 */
export function SelfieCapture({ onUploaded }: { onUploaded: (storageKey: string | null) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function handle(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    onUploaded(null);
    try {
      const photo = await prepareImage(file);
      const { url } = await uploadFile("/media/upload?purpose=kyc", photo);
      setPreview(URL.createObjectURL(photo));
      onUploaded(url);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "The selfie couldn't be uploaded. Try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm font-medium text-ink">Take a selfie</div>
      <p className="text-xs text-ink-soft">
        Face the camera in good light, no glasses or cap. Tailora checks it matches the photo on your NIN
        record and your profile photo, so nobody else can use your identity.
      </p>
      <div className="flex items-center gap-3">
        {preview && <img src={preview} alt="Your selfie" className="h-20 w-16 rounded-lg border border-line object-cover" />}
        <input ref={inputRef} type="file" accept="image/*" capture="user" className="hidden" aria-label="Selfie"
          onChange={(e) => void handle(e)} />
        <Button type="button" variant="secondary" size="sm" isLoading={busy} onClick={() => inputRef.current?.click()}>
          {preview ? "Retake selfie" : "Take selfie"}
        </Button>
      </div>
      {error && <p role="alert" className="text-xs text-thread">{error}</p>}
    </div>
  );
}

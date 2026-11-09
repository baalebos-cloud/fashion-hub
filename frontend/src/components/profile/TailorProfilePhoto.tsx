import { useRef, useState, type ChangeEvent } from "react";
import { apiClient } from "@/lib/api/client";
import { uploadFile } from "@/lib/storage/file-storage";
import { prepareImage } from "@/lib/media/prepare-image";
import { PHOTO_ACCEPT, validateImageFile } from "@/lib/utils/image";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";

/**
 * Tailor-only avatar flow. Tailor profile photos are resized more aggressively
 * than other uploads, avoiding oversized multipart requests on mobile networks.
 * Do not change the shared uploader or any other role's upload behavior.
 */
export function TailorProfilePhoto({
  currentUrl,
  onUploaded,
}: {
  currentUrl?: string | null;
  onUploaded: (url: string) => void | Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.value = "";
    setError(null);
    setStatus(null);
    const invalid = validateImageFile(file);
    if (invalid) {
      setError(invalid);
      return;
    }
    setBusy(true);
    try {
      // A profile avatar needs much less resolution than a portfolio image.
      // uploadFile still performs its standard validation and preparation.
      const prepared = await prepareImage(file, 1024);
      setStatus("Uploading profile photo…");
      const { url } = await uploadFile("/media/upload?purpose=avatar", prepared);
      if (!url) throw new Error("The upload did not return a photo URL.");
      setStatus("Saving profile photo…");
      await apiClient.patch("/users/me", { profile_photo_url: url });
      await onUploaded(url);
      setStatus("Profile photo updated.");
    } catch (failure) {
      setStatus(null);
      setError(getDisplayErrorMessage(failure, "Could not upload or save your profile photo. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-4">
      {currentUrl && (
        <img src={currentUrl} alt="Your current profile photo" className="h-16 w-16 rounded-lg object-cover" />
      )}
      <div>
        <input
          ref={inputRef}
          type="file"
          accept={PHOTO_ACCEPT}
          aria-label="Choose tailor profile photo"
          className="hidden"
          onChange={(event) => { void handleChange(event); }}
        />
        <Button type="button" variant="secondary" size="sm" isLoading={busy}
          onClick={() => inputRef.current?.click()}>
          {currentUrl ? "Change photo" : "Upload photo"}
        </Button>
        {status && <p role="status" className="mt-1 text-xs text-ink-soft">{status}</p>}
        {error && <p role="alert" className="mt-1 text-xs text-thread">{error}</p>}
      </div>
    </div>
  );
}

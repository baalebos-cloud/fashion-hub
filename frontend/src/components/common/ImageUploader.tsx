import { useRef, useState, type ChangeEvent } from "react";
import { validateImageFile } from "@/lib/utils/image";
import { uploadFile } from "@/lib/storage/file-storage";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Button } from "@/components/ui/button";

export interface ImageUploaderProps {
  uploadEndpoint: string;
  currentImageUrl?: string | null;
  onUploaded: (url: string) => void;
  label?: string;
  onRemove?: () => void;
}

/** Used by ProfilePhoto, DesignUpload, DocumentUpload — validates locally
 * (see lib/utils/image.ts) before ever hitting the network, then delegates
 * the actual upload to the backend's storage integration. */
export function ImageUploader({ uploadEndpoint, currentImageUrl, onUploaded, onRemove, label = "Upload image" }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const validationError = validateImageFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const { url } = await uploadFile(uploadEndpoint, file);
      onUploaded(url);
    } catch (failure) {
      setError(getDisplayErrorMessage(failure, "Image upload failed. Check the file and try again."));
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="flex items-center gap-4">
      {currentImageUrl && <div className="relative"><img src={currentImageUrl} alt="Uploaded preview" className="h-16 w-16 rounded-lg object-cover" />{onRemove && <button type="button" aria-label="Remove uploaded photo" className="absolute -right-2 -top-2 rounded-full border border-line bg-paper px-2" onClick={onRemove}>×</button>}</div>}
      <div>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleFileChange} />
        <Button type="button" variant="secondary" size="sm" isLoading={isUploading} onClick={() => inputRef.current?.click()}>
          {label}
        </Button>
        {isUploading && <p role="status" className="mt-1 text-xs text-ink-soft">Uploading image…</p>}
        {error && <p role="alert" className="mt-1 text-xs text-thread">{error}</p>}
      </div>
    </div>
  );
}

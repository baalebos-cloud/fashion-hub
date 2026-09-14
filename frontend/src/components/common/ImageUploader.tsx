import { useRef, useState, type ChangeEvent } from "react";
import { validateImageFile } from "@/lib/utils/image";
import { uploadFile } from "@/lib/storage/file-storage";
import { Button } from "@/components/ui/button";

export interface ImageUploaderProps {
  uploadEndpoint: string;
  currentImageUrl?: string | null;
  onUploaded: (url: string) => void;
  label?: string;
}

/** Used by ProfilePhoto, DesignUpload, DocumentUpload — validates locally
 * (see lib/utils/image.ts) before ever hitting the network, then delegates
 * the actual upload to the backend's storage integration. */
export function ImageUploader({ uploadEndpoint, currentImageUrl, onUploaded, label = "Upload image" }: ImageUploaderProps) {
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
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="flex items-center gap-4">
      {currentImageUrl && <img src={currentImageUrl} alt="" className="h-16 w-16 rounded-lg object-cover" />}
      <div>
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
        <Button type="button" variant="secondary" size="sm" isLoading={isUploading} onClick={() => inputRef.current?.click()}>
          {label}
        </Button>
        {error && <p className="mt-1 text-xs text-thread">{error}</p>}
      </div>
    </div>
  );
}

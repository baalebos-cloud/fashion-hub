import { useRef, useState, type ChangeEvent } from "react";
import { uploadFile } from "@/lib/storage/file-storage";
import { Button } from "@/components/ui/button";

export interface FileUploaderProps {
  uploadEndpoint: string;
  accept?: string;
  onUploaded: (url: string) => void;
  label?: string;
}

/** Non-image file uploads (KYC/KYB documents). See DocumentUpload.tsx for
 * the verification-specific wrapper around this. */
export function FileUploader({ uploadEndpoint, accept, onUploaded, label = "Upload file" }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

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
    <div>
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={handleFileChange} />
      <Button type="button" variant="secondary" size="sm" isLoading={isUploading} onClick={() => inputRef.current?.click()}>
        {label}
      </Button>
      {error && <p className="mt-1 text-xs text-thread">{error}</p>}
    </div>
  );
}

import { useRef, useState, type ChangeEvent } from "react";
import { uploadFile } from "@/lib/storage/file-storage";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

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
  const [uploadedName, setUploadedName] = useState<string | null>(null);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError(null);
    setIsUploading(true);
    try {
      const { url } = await uploadFile(uploadEndpoint, file);
      onUploaded(url);
      setUploadedName(file.name);
    } catch (failure) {
      setError(getDisplayErrorMessage(failure, "Upload failed. Check your connection, file type and storage settings."));
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div>
      <input ref={inputRef} type="file" accept={accept} className="hidden" onChange={handleFileChange} />
      <Button type="button" variant="secondary" size="sm" isLoading={isUploading} onClick={() => inputRef.current?.click()}>
        {label}
      </Button>
      {isUploading && <p role="status" className="mt-1 text-xs text-ink-soft">Uploading securely…</p>}
      {uploadedName && !isUploading && <p role="status" className="mt-1 text-xs text-ink-soft">Uploaded: {uploadedName}</p>}
      {error && <p role="alert" className="mt-1 text-xs text-thread">{error} Choose the file again to retry.</p>}
    </div>
  );
}

import { FileUploader } from "@/components/common/FileUploader";

export function DocumentUpload({ label, onUploaded }: { label: string; onUploaded: (url: string) => void }) {
  return <FileUploader uploadEndpoint="/kyc/upload-id" accept="image/jpeg,image/png,image/webp,application/pdf" label={label} onUploaded={onUploaded} />;
}

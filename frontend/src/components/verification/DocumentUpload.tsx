import { FileUploader } from "@/components/common/FileUploader";

export function DocumentUpload({ label, onUploaded }: { label: string; onUploaded: (url: string) => void }) {
  return <FileUploader uploadEndpoint="/kyc/documents" accept="image/*,application/pdf" label={label} onUploaded={onUploaded} />;
}

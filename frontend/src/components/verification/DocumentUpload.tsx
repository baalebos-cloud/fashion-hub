import { FileUploader } from "@/components/common/FileUploader";

export function DocumentUpload({ label, onUploaded, purpose = "kyc" }: { label: string; onUploaded: (url: string) => void; purpose?: "kyc" | "kyb" }) {
  return <FileUploader uploadEndpoint={`/media/upload?purpose=${purpose}`} accept="image/jpeg,image/png,image/webp,application/pdf" label={label} onUploaded={onUploaded} />;
}

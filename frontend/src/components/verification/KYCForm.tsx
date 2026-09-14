import { useState } from "react";
import { useKYC } from "@/hooks/use-kyc";
import { DocumentUpload } from "./DocumentUpload";
import { VerificationStatus } from "./VerificationStatus";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const ID_TYPES = ["national_id", "passport", "drivers_license"];

export function KYCForm() {
  const { status, isLoading, submit } = useKYC();
  const [idType, setIdType] = useState(ID_TYPES[0]);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!documentUrl) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await submit(idType, [documentUrl]);
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return null;

  if (status && status.status !== "rejected") {
    return <VerificationStatus status={status.status} />;
  }

  return (
    <div className="flex max-w-sm flex-col gap-3">
      {status?.status === "rejected" && (
        <p className="text-sm text-thread">Your previous submission was rejected{status.rejection_reason ? `: ${status.rejection_reason}` : "."} Please resubmit.</p>
      )}
      <Select value={idType} onChange={(e) => setIdType(e.target.value)}>
        {ID_TYPES.map((type) => (
          <option key={type} value={type}>{type.replace(/_/g, " ")}</option>
        ))}
      </Select>
      <DocumentUpload label="Upload ID document" onUploaded={setDocumentUrl} />
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!documentUrl}>Submit for review</Button>
    </div>
  );
}

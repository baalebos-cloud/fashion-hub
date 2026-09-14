import { useState } from "react";
import { useKYB } from "@/hooks/use-kyb";
import { DocumentUpload } from "./DocumentUpload";
import { VerificationStatus } from "./VerificationStatus";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export function KYBForm() {
  const { status, isLoading, submit } = useKYB();
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!documentUrl || !registrationNumber) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await submit(registrationNumber, [documentUrl]);
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
      <Input placeholder="Business registration number" value={registrationNumber} onChange={(e) => setRegistrationNumber(e.target.value)} />
      <DocumentUpload label="Upload registration certificate" onUploaded={setDocumentUrl} />
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!documentUrl || !registrationNumber}>Submit for review</Button>
    </div>
  );
}

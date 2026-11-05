import { useState } from "react";
import { useKYB } from "@/hooks/use-kyb";
import { DocumentUpload } from "./DocumentUpload";
import { VerificationStatus } from "./VerificationStatus";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";

export function KYBForm() {
  const { status, isLoading, submit } = useKYB();
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isProviderError, setIsProviderError] = useState(false);

  async function handleSubmit() {
    if (!documentUrl || !registrationNumber) return;
    setIsSubmitting(true);
    setError(null);
    setIsProviderError(false);
    try {
      await submit(registrationNumber, [documentUrl]);
    } catch (err) {
      const isProvider = isApiError(err) && err.code === "external_provider_error";
      setIsProviderError(isProvider);
      setError(getDisplayErrorMessage(err, "Couldn't submit for business verification. Check your details and try again."));
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
      <label htmlFor="kyb-reg" className="flex flex-col gap-1 text-sm font-medium text-ink">
        Business registration number
        <Input
          id="kyb-reg"
          placeholder="e.g. RC-1234567"
          value={registrationNumber}
          onChange={(e) => setRegistrationNumber(e.target.value)}
        />
      </label>
      <DocumentUpload label="Upload registration certificate" purpose="kyb" onUploaded={setDocumentUrl} />
      {error && (
        <div
          role="alert"
          className={`rounded-card border p-3 text-sm ${
            isProviderError
              ? "border-[#eac9c2] bg-[#fbecea] text-thread"
              : "border-line bg-muslin text-thread"
          }`}
        >
          {error}
          {isProviderError && (
            <p className="mt-1 text-xs text-ink-soft">
              This is a configuration issue — retrying will not help. Contact support.
            </p>
          )}
        </div>
      )}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!documentUrl || !registrationNumber || isProviderError}>Submit for review</Button>
    </div>
  );
}

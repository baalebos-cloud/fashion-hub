import { useState } from "react";
import { useKYB } from "@/hooks/use-kyb";
import { DocumentUpload } from "./DocumentUpload";
import { VerificationStatus } from "./VerificationStatus";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";
import type { CompanyType } from "@/types/kyb";

const COMPANY_TYPES: { value: CompanyType; label: string; example: string }[] = [
  { value: "RC", label: "Limited company (RC)", example: "RC 1234567" },
  { value: "BN", label: "Business name (BN)", example: "BN 1234567" },
  { value: "IT", label: "Incorporated trustees (IT)", example: "IT 123456" },
];

export function KYBForm({ onSubmitted }: { onSubmitted?: () => void } = {}) {
  const { status, isLoading, submit } = useKYB();
  const [companyType, setCompanyType] = useState<CompanyType>("RC");
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isProviderError, setIsProviderError] = useState(false);
  const example = COMPANY_TYPES.find((t) => t.value === companyType)!.example;

  async function handleSubmit() {
    if (!documentUrl || !registrationNumber.trim()) return;
    setIsSubmitting(true);
    setError(null);
    setIsProviderError(false);
    try {
      await submit(registrationNumber.trim(), companyType, [documentUrl]);
      onSubmitted?.();
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
    return (
      <div className="flex flex-col gap-2">
        <VerificationStatus status={status.status} />
        {status.verified_company_name && (
          <p className="text-xs text-ink-soft">
            CAC record found: <span className="font-medium text-ink">{status.verified_company_name}</span>
            {status.name_match === false && " (this differs from your shop name, so a reviewer will check it)"}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex max-w-sm flex-col gap-3">
      {status?.status === "rejected" && (
        <p className="text-sm text-thread">Your previous submission was rejected{status.rejection_reason ? `: ${status.rejection_reason}` : "."} Please resubmit.</p>
      )}
      <label htmlFor="kyb-type" className="flex flex-col gap-1 text-sm font-medium text-ink">
        Business type
        <select id="kyb-type" value={companyType} onChange={(e) => setCompanyType(e.target.value as CompanyType)}
          className="w-full rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink focus:border-brass focus:outline-none">
          {COMPANY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </label>
      <label htmlFor="kyb-reg" className="flex flex-col gap-1 text-sm font-medium text-ink">
        CAC registration number
        <Input
          id="kyb-reg"
          placeholder={`e.g. ${example}`}
          value={registrationNumber}
          onChange={(e) => setRegistrationNumber(e.target.value)}
          autoComplete="off"
          aria-describedby="kyb-reg-help"
        />
      </label>
      <p id="kyb-reg-help" className="-mt-2 text-xs text-ink-soft">We check this against the CAC register.</p>
      <DocumentUpload label="Upload your CAC certificate" purpose="kyb" onUploaded={setDocumentUrl} />
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
      <Button onClick={handleSubmit} isLoading={isSubmitting}
        disabled={!documentUrl || !registrationNumber.trim() || isProviderError}>Submit for review</Button>
    </div>
  );
}

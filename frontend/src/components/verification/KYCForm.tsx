import { useState } from "react";
import { useKYC } from "@/hooks/use-kyc";
import { DocumentUpload } from "./DocumentUpload";
import { VerificationStatus } from "./VerificationStatus";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { formatDate } from "@/lib/formatters/date";
import { useTimezone } from "@/hooks/use-timezone";

/**
 * NIN is compulsory -- there is no "skip" or alternate ID type option.
 * See backend/docs/nin-verification.md: submitting hands the NIN to a
 * government-backed lookup, and the name/DOB/gender that comes BACK from
 * that lookup (not what's typed here) is what gets stored and shown to
 * an admin during review.
 */
export function KYCForm() {
  const { status, isLoading, submit } = useKYC();
  const timeZone = useTimezone();

  const [ninNumber, setNinNumber] = useState("");
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [homeLocation, setHomeLocation] = useState<{ latitude: number; longitude: number; formatted_address?: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!documentUrl || !homeLocation || ninNumber.length !== 11) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await submit({
        nin_number: ninNumber,
        document_storage_keys: [documentUrl],
        home_latitude: homeLocation.latitude,
        home_longitude: homeLocation.longitude,
        home_formatted_address: homeLocation.formatted_address,
      });
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Couldn't verify that NIN. Please double-check the number and try again."));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) return null;

  if (status && status.status !== "rejected") {
    return (
      <div className="flex flex-col gap-3">
        <VerificationStatus status={status.status} />
        {status.nin_verified_full_name && (
          <div className="rounded-card border border-line p-3 text-sm">
            <div className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-soft">Verified against your NIN</div>
            <div className="text-ink">{status.nin_verified_full_name}</div>
            {status.nin_verified_date_of_birth && (
              <div className="text-ink-soft">Born {formatDate(status.nin_verified_date_of_birth, timeZone)}</div>
            )}
            {status.nin_verified_gender && <div className="text-ink-soft capitalize">{status.nin_verified_gender.toLowerCase()}</div>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex max-w-sm flex-col gap-4">
      {status?.status === "rejected" && (
        <p className="text-sm text-thread">
          Your previous submission was rejected{status.rejection_reason ? `: ${status.rejection_reason}` : "."} Please resubmit.
        </p>
      )}

      <div>
        <label htmlFor="nin" className="mb-1.5 block text-sm font-medium text-ink">National Identity Number (NIN)</label>
        <Input
          id="nin"
          value={ninNumber}
          onChange={(e) => setNinNumber(e.target.value.replace(/\D/g, "").slice(0, 11))}
          placeholder="11-digit NIN"
          inputMode="numeric"
          maxLength={11}
        />
        <p className="mt-1 text-xs text-ink-soft">
          Your name, date of birth, and gender are pulled directly from your NIN record — you don't need to re-type them.
        </p>
      </div>

      <DocumentUpload label="Upload a photo of your ID" onUploaded={setDocumentUrl} />

      <div>
        <div className="mb-1.5 text-sm font-medium text-ink">Home address</div>
        <MapLocationPicker
          onSelect={(location) =>
            setHomeLocation({ latitude: location.latitude, longitude: location.longitude, formatted_address: location.formatted_address ?? undefined })
          }
        />
        {homeLocation?.formatted_address && <p className="mt-1 text-xs text-ink-soft">{homeLocation.formatted_address}</p>}
      </div>

      {error && <p className="text-sm text-thread">{error}</p>}

      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!documentUrl || !homeLocation || ninNumber.length !== 11}>
        Submit for verification
      </Button>
    </div>
  );
}

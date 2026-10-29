import { useState } from "react";
import { z } from "zod";
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
  const [useManualAddress, setUseManualAddress] = useState(true);
  const [manualAddress, setManualAddress] = useState({ street: "", city: "", state: "", landmark: "" });
  const manualSchema = z.object({
    street: z.string().trim().min(5),
    city: z.string().trim().min(2),
    state: z.string().trim().min(2),
    landmark: z.string(),
  });
  const validManual = useManualAddress && manualSchema.safeParse(manualAddress).success;
  const validNin = /^\d{11}$/.test(ninNumber);
  const canSubmit = Boolean(documentUrl) && validNin && (validManual || (!useManualAddress && homeLocation !== null));
  const address = validManual
    ? [manualAddress.street, manualAddress.landmark, manualAddress.city, manualAddress.state, "Nigeria"].filter(Boolean).join(", ")
    : homeLocation?.formatted_address;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!canSubmit || !documentUrl) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await submit({
        nin_number: ninNumber,
        document_storage_keys: [documentUrl],
        home_latitude: useManualAddress ? null : homeLocation?.latitude ?? null,
        home_longitude: useManualAddress ? null : homeLocation?.longitude ?? null,
        home_formatted_address: address ?? undefined,
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
      {documentUrl && <p role="status" className="text-sm text-ink-soft">ID document uploaded successfully.</p>}

      <div>
        <div className="mb-1.5 text-sm font-medium text-ink">Home address</div>
        <fieldset className="mb-3">
          <legend className="mb-2 text-sm text-ink-soft">Choose how to provide your home address</legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button type="button" aria-pressed={useManualAddress}
              className={`min-h-11 rounded-lg border px-3 py-2 text-sm ${useManualAddress ? "border-ink bg-muslin font-semibold" : "border-line"}`}
              onClick={() => { setUseManualAddress(true); setError(null); }}>
              Enter address manually
            </button>
            <button type="button" aria-pressed={!useManualAddress}
              className={`min-h-11 rounded-lg border px-3 py-2 text-sm ${!useManualAddress ? "border-ink bg-muslin font-semibold" : "border-line"}`}
              onClick={() => { setUseManualAddress(false); setError(null); }}>
              Choose on map
            </button>
          </div>
        </fieldset>
        {!useManualAddress && (
          <MapLocationPicker
            onSelect={(location) => setHomeLocation({
              latitude: location.latitude, longitude: location.longitude,
              formatted_address: location.formatted_address ?? undefined,
            })}
          />
        )}
        {useManualAddress && (
          <div className="mt-3 flex flex-col gap-2">
            {(["street", "city", "state", "landmark"] as const).map((field) => (
              <label key={field} className="text-sm">
                <span className="mb-1 block capitalize">{field === "landmark" ? "Postal code or landmark (optional)" : field === "city" ? "City / LGA" : field === "state" ? "State" : "Street address"}</span>
                <Input value={manualAddress[field]} onChange={(e) => setManualAddress((prev) => ({ ...prev, [field]: e.target.value }))} />
              </label>
            ))}
            <p className="text-xs text-ink-soft">Your address will be saved for review. GPS coordinates remain unverified until geocoding succeeds.</p>
          </div>
        )}
        {!useManualAddress && homeLocation?.formatted_address && <p className="mt-1 text-xs text-ink-soft">{homeLocation.formatted_address}</p>}
      </div>

      {error && <p className="text-sm text-thread">{error}</p>}

      {!canSubmit && <p className="text-xs text-ink-soft" role="status">To submit, enter an 11-digit NIN, upload your ID, and complete your home address using the manual fields or map.</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!canSubmit || isSubmitting}>
        Submit for verification
      </Button>
    </div>
  );
}

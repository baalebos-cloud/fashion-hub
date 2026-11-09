import { useState } from "react";
import { z } from "zod";
import { useKYC } from "@/hooks/use-kyc";
import { DocumentUpload } from "./DocumentUpload";
import { SelfieCapture } from "./SelfieCapture";
import { VerificationStatus } from "./VerificationStatus";
import { AddressMapPicker } from "@/components/common/AddressMapPicker";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { isApiError } from "@/lib/api/errors";
import { formatDate } from "@/lib/formatters/date";
import { useTimezone } from "@/hooks/use-timezone";

/**
 * NIN is compulsory -- there is no "skip" or alternate ID type option.
 * See backend/docs/nin-verification.md: submitting hands the NIN to a
 * government-backed lookup, and the name/DOB/gender that comes BACK from
 * that lookup (not what's typed here) is what gets stored and shown to
 * an admin during review.
 */
export function KYCForm({ onSubmitted }: { onSubmitted?: () => void } = {}) {
  const { status, isLoading, submit } = useKYC();
  const timeZone = useTimezone();

  const [ninNumber, setNinNumber] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [selfieKey, setSelfieKey] = useState<string | null>(null);
  const [homeLocation, setHomeLocation] = useState<{ latitude: number; longitude: number; formatted_address?: string } | null>(null);
  const [useManualAddress, setUseManualAddress] = useState(true);
  const [manualAddress, setManualAddress] = useState({ street: "", city: "", state: "", landmark: "" });
  const manualSchema = z.object({
    street: z.string().trim().min(5),
    city: z.string().trim().min(2),
    state: z.string().trim().min(2),
    landmark: z.string(),
  });
  const validManual = manualSchema.safeParse(manualAddress).success;
  const validNin = /^\d{11}$/.test(ninNumber);
  const today = new Date().toISOString().slice(0, 10);
  const validDob = /^\d{4}-\d{2}-\d{2}$/.test(dateOfBirth) && dateOfBirth >= "1900-01-01" && dateOfBirth <= today;
  const canSubmit = Boolean(documentUrl) && Boolean(selfieKey) && validNin && validDob && validManual && (useManualAddress || homeLocation !== null);
  const address = [manualAddress.street, manualAddress.landmark, manualAddress.city, manualAddress.state, "Nigeria"].filter(Boolean).join(", ");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isProviderError, setIsProviderError] = useState(false);

  async function handleSubmit() {
    if (!canSubmit || !documentUrl) return;
    setIsSubmitting(true);
    setError(null);
    setIsProviderError(false);
    try {
      await submit({
        nin_number: ninNumber,
        document_storage_keys: [documentUrl],
        home_latitude: useManualAddress ? null : homeLocation?.latitude ?? null,
        home_longitude: useManualAddress ? null : homeLocation?.longitude ?? null,
        home_formatted_address: address ?? undefined,
        date_of_birth: dateOfBirth,
        selfie_storage_key: selfieKey ?? undefined,
      });
      onSubmitted?.();
    } catch (err) {
      const isProvider = isApiError(err) && err.code === "external_provider_error";
      setIsProviderError(isProvider);
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
        {status.auto_approved && (
          <p role="status" className="rounded-control bg-success-wash px-3 py-2 text-sm text-success">
            Your NIN details, ID and face matched, so you were verified straight away.
          </p>
        )}
        {status.status === "under_review" && (
          <p className="text-sm text-ink-soft">Our team is checking your details by hand. You'll get a notification when it's done.</p>
        )}
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
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          maxLength={11}
        />
        <p className="mt-1 text-xs text-ink-soft">
          We look up your NIN record and compare it with your account. If your name and date of birth match, you're verified straight away.
        </p>
      </div>

      <div>
        <label htmlFor="date-of-birth" className="mb-1.5 block text-sm font-medium text-ink">Date of birth (as on your NIN)</label>
        <Input id="date-of-birth" type="date" min="1900-01-01" max={today} value={dateOfBirth}
          onChange={(e) => setDateOfBirth(e.target.value)} aria-describedby="date-of-birth-hint" />
        <p id="date-of-birth-hint" className="mt-1 text-xs text-ink-soft">Used only to check against your NIN record.</p>
      </div>

      <DocumentUpload label="Upload a photo of your ID" onUploaded={setDocumentUrl} />
      {documentUrl && <p role="status" className="text-sm text-ink-soft">ID document uploaded successfully.</p>}

      <SelfieCapture onUploaded={setSelfieKey} />

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
          <AddressMapPicker label="Home address" onAddressSelect={(location) => {
            setHomeLocation({ latitude: location.latitude, longitude: location.longitude, formatted_address: location.formatted_address ?? undefined });
            setManualAddress((old) => ({ ...old,
              street: location.formatted_address ?? "",
              city: location.city ?? "", state: location.state_region ?? "",
            }));
          }} />
        )}
        {(
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

      </div>

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

      {!canSubmit && !error && <p className="text-xs text-ink-soft" role="status">To submit, enter an 11-digit NIN and your date of birth, upload your ID, take a selfie, and complete your home address using the address fields below the map or manually.</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} disabled={!canSubmit || isSubmitting || isProviderError}>
        Submit for verification
      </Button>
    </div>
  );
}

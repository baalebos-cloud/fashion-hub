import { useEffect, useState, type ComponentProps } from "react";
import { MapLocationPicker } from "@/components/checkout/MapLocationPicker";
import { LocationSummary } from "@/components/profile/LocationSummary";
import { professionalsApi } from "@/api/professionals.api";
import { useToast } from "@/components/ui/toast";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { GeoLocation } from "@/types/location";

type SavedLocation = Pick<GeoLocation, "latitude" | "longitude" | "formatted_address" | "city" | "state_region" | "country">;

export default function Location() {
  const { showToast } = useToast();
  const [saved, setSaved] = useState<SavedLocation | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [disclosureOpen, setDisclosureOpen] = useState(false);

  // Load the professional's profile on mount so we can show any previously
  // saved location. The Professional type doesn't carry location data back
  // from the API yet, so we only show what was saved in this session.
  useEffect(() => {
    professionalsApi.mine().catch(() => {
      // Non-fatal — page still works without pre-loaded location.
    });
  }, []);

  async function handleSelect(
    location: Parameters<ComponentProps<typeof MapLocationPicker>["onSelect"]>[0],
  ) {
    setIsSaving(true);
    try {
      await professionalsApi.updateMyLocation({
        latitude: location.latitude,
        longitude: location.longitude,
        formattedAddress: location.formatted_address ?? undefined,
      });
      setSaved(location);
      showToast("Business location saved.", "success");
    } catch (err) {
      showToast(getDisplayErrorMessage(err, "Couldn't save your location."), "error");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-1 font-display text-xl text-ink">Shop location</h1>
      <p className="mb-5 text-sm text-ink-soft">
        Pick your shop or workspace on the map — this is what customers use to find you and what
        delivery partners use for pickup.
      </p>

      {saved && (
        <div className="mb-4 rounded-card border border-line bg-paper p-3">
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-soft">
            Saved location
          </p>
          <LocationSummary location={saved} />
        </div>
      )}

      <MapLocationPicker onSelect={handleSelect} />

      {isSaving && (
        <p role="status" className="mt-2 text-sm text-ink-soft">
          Saving location…
        </p>
      )}

      {/* Verification disclosure */}
      <div className="mt-6 rounded-card border border-line bg-muslin">
        <button
          type="button"
          aria-expanded={disclosureOpen}
          aria-controls="location-verification-panel"
          onClick={() => setDisclosureOpen((o) => !o)}
          className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-ink"
        >
          How does verification work?
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
            className={`flex-shrink-0 text-ink-soft transition-transform duration-150 ${disclosureOpen ? "rotate-180" : ""}`}
          >
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        {disclosureOpen && (
          <div id="location-verification-panel" className="border-t border-line px-4 pb-4 pt-3 text-sm text-ink-soft">
            <p className="mb-2">
              Identity verification (KYC) and business verification (KYB) are separate processes.
              Setting your shop location here does <strong className="text-ink">not</strong> complete
              either verification.
            </p>
            <p className="mb-2">
              To verify your identity, open{" "}
              <a href="/app/professional/verification" className="text-brass underline underline-offset-2">
                Verification
              </a>{" "}
              and follow the instructions there.
            </p>
            <p>
              The business-verification (KYB) process is not yet fully available. Contact support if
              you need an official verification decision.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

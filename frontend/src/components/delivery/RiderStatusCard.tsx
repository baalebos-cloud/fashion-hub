import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deliveryPartnersApi, type RiderProfile, type VehicleType } from "@/api/delivery-partners.api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { VerificationBadge } from "@/components/profile/VerificationBadge";
import { deliveryRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

const VEHICLES: { value: VehicleType; label: string }[] = [
  { value: "bike", label: "Motorbike" }, { value: "car", label: "Car" },
  { value: "van", label: "Van" }, { value: "foot", label: "On foot" },
];

/**
 * Uber-style online/offline control. Saved on the server, so going online
 * actually makes the rider eligible for jobs; explains exactly why when not.
 */
export function RiderStatusCard({ onChange }: { onChange?: (profile: RiderProfile) => void }) {
  const [profile, setProfile] = useState<RiderProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    deliveryPartnersApi.me().then(setProfile).catch(() => setError("Your rider profile couldn't be loaded."));
  }, []);

  async function run(action: () => Promise<RiderProfile>) {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setProfile(next);
      onChange?.(next);
    } catch (err) {
      setError(getDisplayErrorMessage(err, "That didn't work. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  if (!profile) {
    return error ? <Card><p role="alert" className="text-sm text-thread">{error}</p></Card> : null;
  }

  const online = profile.is_available;
  const blocker = !profile.vehicle_type ? "vehicle" : !profile.is_verified ? "verification" : null;

  return (
    <Card className={online ? "border-success/30 bg-success-wash/60 p-5" : "p-5"} role="region" aria-label="Rider status">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${online ? "bg-success" : "bg-line-strong"}`} />
            <p className="font-display text-lg text-ink">{online ? "You're online" : "You're offline"}</p>
            {profile.is_verified && <VerificationBadge />}
          </div>
          <p className="mt-0.5 text-xs text-ink-soft">
            {online ? "You'll see new delivery jobs and can make offers." : "Go online to start receiving delivery jobs."}
          </p>
        </div>
        <button type="button" role="switch" aria-checked={online} aria-label={online ? "Go offline" : "Go online"}
          disabled={busy || (!online && blocker !== null)}
          onClick={() => void run(() => deliveryPartnersApi.setAvailability(!online))}
          className={`relative h-8 w-14 shrink-0 rounded-full transition-colors disabled:opacity-50 ${online ? "bg-success" : "bg-line-strong"}`}>
          <span className={`absolute top-1 h-6 w-6 rounded-full bg-surface shadow transition-all ${online ? "left-7" : "left-1"}`} />
        </button>
      </div>

      {blocker === "vehicle" && (
        <div className="mt-4">
          <p className="text-sm text-ink">How do you deliver?</p>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {VEHICLES.map((v) => (
              <Button key={v.value} size="sm" variant="secondary" disabled={busy}
                onClick={() => void run(() => deliveryPartnersApi.saveVehicle(v.value))}>{v.label}</Button>
            ))}
          </div>
        </div>
      )}
      {blocker === "verification" && (
        <p className="mt-4 rounded-control bg-warning-wash px-3 py-2 text-[13px] text-warning">
          You can go online once your identity is verified.{" "}
          <Link to={deliveryRoutes.verification} className="font-medium underline">Check verification</Link>
        </p>
      )}
      {error && <p role="alert" className="mt-3 text-xs text-thread">{error}</p>}
    </Card>
  );
}

import { Button } from "@/components/ui/button";
import { useRiderSharing, type SharingStatus } from "./rider-sharing-context";

const LABEL: Record<SharingStatus, string> = {
  off: "Not sharing", live: "Sharing live", retrying: "Reconnecting…", denied: "Location permission off", no_signal: "Waiting for GPS",
};

/** Start/stop sharing for one delivery. The sharing itself runs in RiderSharingProvider, so it keeps
 * going when the rider moves to another screen. */
export function RiderGpsSharing({ deliveryId }: { deliveryId: string }) {
  const sharing = useRiderSharing();
  const mine = sharing.deliveryId === deliveryId;
  const status: SharingStatus = mine ? sharing.status : "off";

  return (
    <section className="space-y-3 rounded-card border border-line p-4" aria-label="Rider GPS sharing">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium text-ink">Live location sharing</h2>
        <span className={`rounded-full px-2 py-0.5 text-xs ${status === "live" ? "bg-brass/20 text-ink" : status === "off" ? "bg-muslin text-ink-soft" : "bg-thread/10 text-thread"}`}
          data-testid="gps-status">{LABEL[status]}</span>
      </div>
      <p className="text-sm text-ink-soft">
        Share while delivering so the customer can follow you. They see your recent location until handover. Nothing is saved to your profile.
      </p>
      {status === "off"
        ? <Button disabled={sharing.busy} isLoading={sharing.busy} onClick={() => void sharing.start(deliveryId)}>Start sharing my location</Button>
        : <Button variant="secondary" disabled={sharing.busy} onClick={() => void sharing.stop()}>Stop sharing</Button>}
      {sharing.message && (mine || status === "off") && <p role="status" className="text-sm text-ink-soft">{sharing.message}</p>}
      {status !== "off" && (
        <p className="text-xs text-ink-soft">
          {sharing.lastSent ? `Last sent ${sharing.lastSent.toLocaleTimeString()}. ` : ""}
          Sharing continues while you use other Tailora screens. Keep the app open with the screen on: phones pause location for apps in the background.
        </p>
      )}
    </section>
  );
}

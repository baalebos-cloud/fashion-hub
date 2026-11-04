import { useEffect, useRef, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { Button } from "@/components/ui/button";

/**
 * Rider-initiated sharing only. The token is kept in memory, not localStorage.
 * The backend expires points within 90 seconds and atomically revokes consent.
 */
export function RiderGpsSharing({ deliveryId }: { deliveryId: string }) {
  const [sharing, setSharing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);
  const consentToken = useRef<string | null>(null);
  const lastReport = useRef(0);

  useEffect(() => () => {
    if (watchId.current !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId.current);
    }
    watchId.current = null;
    if (consentToken.current) {
      consentToken.current = null;
      void deliveriesApi.stopPosition(deliveryId).catch(() => {
        // The last point expires on the server in 90 seconds regardless.
      });
    }
  }, [deliveryId]);

  async function begin() {
    if (!navigator.geolocation) {
      setMessage("Your browser does not support location sharing.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const token = await deliveriesApi.startPosition(deliveryId);
      consentToken.current = token;
      lastReport.current = 0;
      watchId.current = navigator.geolocation.watchPosition(
        (position) => {
          if (!consentToken.current || Date.now() - lastReport.current < 15000) return;
          if (position.coords.accuracy > 200) {
            setMessage("GPS accuracy is too low. Move outdoors or try again.");
            return;
          }
          lastReport.current = Date.now();
          void deliveriesApi.publishPosition(deliveryId, {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy_m: position.coords.accuracy,
            share_token: token,
          }).then(() => setMessage(null)).catch(() => {
            setMessage("Unable to share GPS. Check your connection or restart sharing.");
          });
        },
        (error) => {
          setMessage(error.code === 1
            ? "Location permission denied. Enable location for this site to share your trip."
            : "GPS position is unavailable. Check your device and try again.");
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
      );
      setSharing(true);
    } catch {
      consentToken.current = null;
      setMessage("Unable to start GPS sharing. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function stop() {
    const id = watchId.current;
    watchId.current = null;
    consentToken.current = null;
    if (id !== null && navigator.geolocation) navigator.geolocation.clearWatch(id);
    setSharing(false);
    setBusy(true);
    try {
      await deliveriesApi.stopPosition(deliveryId);
      setMessage("GPS sharing stopped.");
    } catch {
      setMessage("Unable to confirm GPS sharing stopped. The last position expires automatically.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-card border border-line p-4" aria-label="Rider GPS sharing">
      <h2 className="font-medium text-ink">Live location sharing</h2>
      <p className="text-sm text-ink-soft">
        Start sharing only while delivering. Your customer can see recent coordinates.
        No position is stored in your long-term profile.
      </p>
      {sharing
        ? <Button variant="secondary" disabled={busy} onClick={() => void stop()}>Stop sharing</Button>
        : <Button disabled={busy} isLoading={busy} onClick={() => void begin()}>Start sharing my location</Button>}
      {message && <p role="status" className="text-sm text-ink-soft">{message}</p>}
      {sharing && <p className="text-xs text-ink-soft">Sharing while this page stays open. Location expires within 90 seconds after updates stop.</p>}
    </section>
  );
}

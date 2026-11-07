import { useEffect, useRef, useState } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { isApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";

const MOVING_INTERVAL_MS = 10_000;   // send every 10 s while moving
const STILL_INTERVAL_MS = 30_000;    // every 30 s while stopped (saves battery and data)
const MOVING_SPEED_MPS = 2;          // ~7 km/h
const MAX_BACKOFF_MS = 60_000;

type Status = "off" | "live" | "retrying" | "denied" | "no_signal";

interface Pending { latitude: number; longitude: number; accuracy_m: number; recorded_at: string; speed_mps?: number }

/**
 * Rider-initiated sharing only. The consent token lives in memory, never in storage.
 *
 * Browsers only give location while this page is open and the screen is on; they pause it in
 * the background. We keep the screen awake while sharing (where the browser allows) and say so.
 * Reliable background tracking needs a native app (see docs/logistics-tracking.md).
 */
export function RiderGpsSharing({ deliveryId }: { deliveryId: string }) {
  const [status, setStatus] = useState<Status>("off");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [lastSent, setLastSent] = useState<Date | null>(null);
  const watchId = useRef<number | null>(null);
  const token = useRef<string | null>(null);
  const pending = useRef<Pending | null>(null);
  const lastSentAt = useRef(0);
  const backoff = useRef(0);
  const retryTimer = useRef<number | null>(null);
  const wakeLock = useRef<{ release: () => Promise<void> } | null>(null);
  const restarted = useRef(false);

  function clearRetry() {
    if (retryTimer.current !== null) window.clearTimeout(retryTimer.current);
    retryTimer.current = null;
  }

  async function holdScreenAwake() {
    try {
      const nav = navigator as Navigator & { wakeLock?: { request: (t: "screen") => Promise<{ release: () => Promise<void> }> } };
      wakeLock.current = (await nav.wakeLock?.request("screen")) ?? null;
    } catch {
      wakeLock.current = null; // not supported or refused: the note below still applies
    }
  }

  async function reportState(state: "permission_denied" | "unavailable" | "paused") {
    if (!token.current) return;
    await deliveriesApi.reportPositionState(deliveryId, token.current, state).catch(() => undefined);
  }

  async function flush() {
    const point = pending.current;
    if (!point || !token.current) return;
    clearRetry();
    try {
      const result = await deliveriesApi.publishPosition(deliveryId, { ...point, share_token: token.current });
      if (pending.current === point) pending.current = null;
      backoff.current = 0;
      restarted.current = false;
      if (result.accepted !== false) { lastSentAt.current = Date.now(); setLastSent(new Date()); }
      setStatus("live");
      setMessage(null);
    } catch (err) {
      if (isApiError(err) && err.status === 403 && !restarted.current) {
        // Sharing lapsed (e.g. after a long pause): start a fresh session once, then resend.
        restarted.current = true;
        try {
          token.current = await deliveriesApi.startPosition(deliveryId);
          void flush();
          return;
        } catch { /* fall through to retry */ }
      }
      if (isApiError(err) && err.status === 422) {
        pending.current = null; // that fix was refused (too old); wait for the next one
        return;
      }
      if (isApiError(err) && err.status === 409) {
        void stop("This delivery is no longer in transit, so sharing has stopped.");
        return;
      }
      backoff.current = Math.min(MAX_BACKOFF_MS, backoff.current ? backoff.current * 2 : 5_000);
      setStatus("retrying");
      setMessage("Connection lost. Your latest location will be sent when you're back online.");
      retryTimer.current = window.setTimeout(() => void flush(), backoff.current);
    }
  }

  function onPosition(position: GeolocationPosition) {
    if (!token.current) return;
    if (position.coords.accuracy > 200) {
      setMessage("GPS accuracy is too low. Move outdoors or near a window.");
      return;
    }
    pending.current = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy_m: position.coords.accuracy,
      recorded_at: new Date(position.timestamp).toISOString(),
      ...(position.coords.speed != null && position.coords.speed >= 0 ? { speed_mps: position.coords.speed } : {}),
    };
    const moving = (position.coords.speed ?? 0) >= MOVING_SPEED_MPS;
    const interval = moving ? MOVING_INTERVAL_MS : STILL_INTERVAL_MS;
    if (backoff.current === 0 && Date.now() - lastSentAt.current >= interval) void flush();
  }

  function onError(error: GeolocationPositionError) {
    if (error.code === 1) {
      setStatus("denied");
      setMessage("Location permission is off. Allow location for this site in your browser settings, then start again.");
      void reportState("permission_denied");
    } else {
      setStatus("no_signal");
      setMessage("Can't get a GPS fix right now. We'll keep trying.");
      void reportState("unavailable");
    }
  }

  async function begin() {
    if (!navigator.geolocation) {
      setMessage("Your browser does not support location sharing.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      token.current = await deliveriesApi.startPosition(deliveryId);
      lastSentAt.current = 0;
      backoff.current = 0;
      watchId.current = navigator.geolocation.watchPosition(onPosition, onError,
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
      setStatus("live");
      void holdScreenAwake();
    } catch {
      token.current = null;
      setMessage("Unable to start location sharing. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function stop(note = "Location sharing stopped.") {
    const id = watchId.current;
    watchId.current = null;
    token.current = null;
    pending.current = null;
    clearRetry();
    if (id !== null && navigator.geolocation) navigator.geolocation.clearWatch(id);
    void wakeLock.current?.release().catch(() => undefined);
    wakeLock.current = null;
    setStatus("off");
    setBusy(true);
    try {
      await deliveriesApi.stopPosition(deliveryId);
      setMessage(note);
    } catch {
      setMessage("Couldn't confirm sharing stopped. Your last location disappears automatically.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    const online = () => { if (token.current) { backoff.current = 0; void flush(); } };
    const visible = () => {
      if (!token.current) return;
      if (document.visibilityState === "visible") { void holdScreenAwake(); void flush(); }
      else void reportState("paused");
    };
    window.addEventListener("online", online);
    document.addEventListener("visibilitychange", visible);
    return () => {
      window.removeEventListener("online", online);
      document.removeEventListener("visibilitychange", visible);
      clearRetry();
      if (watchId.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
      void wakeLock.current?.release().catch(() => undefined);
      if (token.current) {
        token.current = null;
        void deliveriesApi.stopPosition(deliveryId).catch(() => undefined);
      }
    };
  }, [deliveryId]); // eslint-disable-line react-hooks/exhaustive-deps

  const label: Record<Status, string> = {
    off: "Not sharing", live: "Sharing live", retrying: "Reconnecting…", denied: "Location permission off", no_signal: "Waiting for GPS",
  };

  return (
    <section className="space-y-3 rounded-card border border-line p-4" aria-label="Rider GPS sharing">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-medium text-ink">Live location sharing</h2>
        <span className={`rounded-full px-2 py-0.5 text-xs ${status === "live" ? "bg-brass/20 text-ink" : status === "off" ? "bg-muslin text-ink-soft" : "bg-thread/10 text-thread"}`}
          data-testid="gps-status">{label[status]}</span>
      </div>
      <p className="text-sm text-ink-soft">
        Share only while delivering. The customer sees your recent location until handover. Nothing is saved to your profile.
      </p>
      {status === "off"
        ? <Button disabled={busy} isLoading={busy} onClick={() => void begin()}>Start sharing my location</Button>
        : <Button variant="secondary" disabled={busy} onClick={() => void stop()}>Stop sharing</Button>}
      {message && <p role="status" className="text-sm text-ink-soft">{message}</p>}
      {status !== "off" && (
        <p className="text-xs text-ink-soft">
          {lastSent ? `Last sent ${lastSent.toLocaleTimeString()}. ` : ""}
          Keep this page open with the screen on. Phones pause location for web pages in the background.
        </p>
      )}
    </section>
  );
}

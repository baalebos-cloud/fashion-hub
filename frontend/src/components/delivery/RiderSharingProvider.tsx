import { useEffect, useRef, useState, type ReactNode } from "react";
import { deliveriesApi } from "@/api/deliveries.api";
import { isApiError } from "@/lib/api/errors";
import { RiderSharingContext, type SharingStatus } from "./rider-sharing-context";

const MOVING_INTERVAL_MS = 10_000;   // send every 10 s while moving
const STILL_INTERVAL_MS = 30_000;    // every 30 s while stopped (saves battery and data)
const MOVING_SPEED_MPS = 2;          // ~7 km/h
const MAX_BACKOFF_MS = 60_000;

interface Pending { latitude: number; longitude: number; accuracy_m: number; recorded_at: string; speed_mps?: number }


/**
 * Rider-initiated location sharing for the whole rider area of the app. It lives above the pages, so
 * sharing keeps going while the rider moves between the job, navigation and drop-off screens (it used
 * to stop the moment they left the page they started it on). It stops when the rider taps Stop, when
 * the job is no longer in transit, or when they leave the rider area (e.g. sign out).
 *
 * The consent token lives in memory, never in storage. Browsers only give location while the app is
 * open and the screen is on; the screen is kept awake while sharing where the browser allows.
 */
export function RiderSharingProvider({ children }: { children: ReactNode }) {
  const [deliveryId, setDeliveryId] = useState<string | null>(null);
  const [status, setStatus] = useState<SharingStatus>("off");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [lastSent, setLastSent] = useState<Date | null>(null);
  const active = useRef<string | null>(null);
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
      wakeLock.current = null; // not supported or refused
    }
  }

  async function reportState(state: "permission_denied" | "unavailable" | "paused") {
    const id = active.current;
    if (!id || !token.current) return;
    await deliveriesApi.reportPositionState(id, token.current, state).catch(() => undefined);
  }

  function release() {
    clearRetry();
    if (watchId.current !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId.current);
    watchId.current = null;
    void wakeLock.current?.release().catch(() => undefined);
    wakeLock.current = null;
    token.current = null;
    pending.current = null;
  }

  async function stop(note = "Location sharing stopped.") {
    const id = active.current;
    release();
    active.current = null;
    setDeliveryId(null);
    setStatus("off");
    if (!id) return;
    setBusy(true);
    try {
      await deliveriesApi.stopPosition(id);
      setMessage(note);
    } catch {
      setMessage("Couldn't confirm sharing stopped. Your last location disappears automatically.");
    } finally {
      setBusy(false);
    }
  }

  async function flush() {
    const id = active.current;
    const point = pending.current;
    if (!id || !point || !token.current) return;
    clearRetry();
    try {
      const result = await deliveriesApi.publishPosition(id, { ...point, share_token: token.current });
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
          token.current = await deliveriesApi.startPosition(id);
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
      setMessage("Location permission is off. Allow location for Tailora in your phone or browser settings, then start again.");
      void reportState("permission_denied");
    } else {
      setStatus("no_signal");
      setMessage("Can't get a GPS fix right now. We'll keep trying.");
      void reportState("unavailable");
    }
  }

  async function start(id: string) {
    if (!navigator.geolocation) {
      setMessage("This device can't share location.");
      return;
    }
    if (active.current && active.current !== id) await stop();
    setBusy(true);
    setMessage(null);
    try {
      token.current = await deliveriesApi.startPosition(id);
      active.current = id;
      setDeliveryId(id);
      lastSentAt.current = 0;
      backoff.current = 0;
      restarted.current = false;
      if (watchId.current !== null) navigator.geolocation.clearWatch(watchId.current);
      watchId.current = navigator.geolocation.watchPosition(onPosition, onError,
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
      setStatus("live");
      void holdScreenAwake();
    } catch (err) {
      token.current = null;
      active.current = null;
      setDeliveryId(null);
      setMessage(isApiError(err) && err.status === 409
        ? "You can share your location once you've picked up the package."
        : "Unable to start location sharing. Check your connection and try again.");
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
      // Leaving the rider area (e.g. signing out) ends sharing.
      const id = active.current;
      release();
      active.current = null;
      if (id) void deliveriesApi.stopPosition(id).catch(() => undefined);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <RiderSharingContext.Provider value={{ deliveryId, status, busy, message, lastSent, start, stop }}>
      {children}
    </RiderSharingContext.Provider>
  );
}

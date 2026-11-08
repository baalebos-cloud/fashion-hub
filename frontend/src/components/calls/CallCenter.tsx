import { useEffect, useRef, useState } from "react";
import { callsApi } from "@/api/calls.api";
import { Button } from "@/components/ui/button";
import { useCallStore } from "@/store/call.store";
import { cn } from "@/lib/utils/cn";

const INCOMING_POLL_MS = 4000;

/** Plays a soft ring (incoming) or ringback (outgoing) pattern with Web Audio; no audio files. */
function useTone(kind: "ring" | "ringback" | null) {
  useEffect(() => {
    if (!kind || typeof window === "undefined" || !("AudioContext" in window)) return;
    let ctx: AudioContext | null = null;
    try { ctx = new AudioContext(); } catch { return; }
    const beep = () => {
      if (!ctx || ctx.state === "closed") return;
      const now = ctx.currentTime;
      const tones = kind === "ring" ? [[440, 0], [480, 0]] : [[425, 0]];
      for (const [freq] of tones) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(kind === "ring" ? 0.08 : 0.04, now + 0.05);
        gain.gain.setValueAtTime(kind === "ring" ? 0.08 : 0.04, now + (kind === "ring" ? 0.9 : 1.0));
        gain.gain.exponentialRampToValueAtTime(0.0001, now + (kind === "ring" ? 1.0 : 1.1));
        osc.connect(gain).connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 1.2);
      }
      if (kind === "ring" && "vibrate" in navigator) navigator.vibrate?.([300, 200, 300]);
    };
    beep();
    const timer = window.setInterval(beep, kind === "ring" ? 3000 : 4000);
    return () => { window.clearInterval(timer); void ctx?.close(); };
  }, [kind]);
}

function useElapsed(since: number | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!since) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [since]);
  if (!since) return null;
  const seconds = Math.max(0, Math.floor((now - since) / 1000));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Checks for calls ringing for this person while the app is open and visible. */
function useIncomingCalls(enabled: boolean) {
  const ring = useCallStore((s) => s.ring);
  const busy = useCallStore((s) => s.phase !== "idle" && s.phase !== "ended");
  useEffect(() => {
    if (!enabled || busy) return;
    let active = true;
    const check = () => {
      if (document.visibilityState !== "visible") return;
      callsApi.incoming().then((calls) => { if (active && calls[0]) ring(calls[0]); }).catch(() => {});
    };
    check();
    const timer = window.setInterval(check, INCOMING_POLL_MS);
    document.addEventListener("visibilitychange", check);
    return () => { active = false; window.clearInterval(timer); document.removeEventListener("visibilitychange", check); };
  }, [enabled, busy, ring]);
}

function MicIcon({ off }: { off: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      {off && <path d="M4 4l16 16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />}
    </svg>
  );
}

/**
 * The call screen for every signed-in page: rings for incoming calls, and shows the
 * call in progress (mute, hang up, timer). Mounted once in the dashboard layout.
 */
export function CallCenter({ enabled = true }: { enabled?: boolean }) {
  useIncomingCalls(enabled);
  const { phase, call, calleeLabel, muted, connectedAt, message, answer, decline, hangUp, toggleMute, dismiss } = useCallStore();
  useTone(phase === "incoming" ? "ring" : phase === "calling" ? "ringback" : null);
  const elapsed = useElapsed(phase === "connected" ? connectedAt : null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (phase !== "idle") headingRef.current?.focus(); }, [phase]);

  useEffect(() => {
    if (phase !== "ended") return;
    const timer = window.setTimeout(dismiss, 6000);
    return () => window.clearTimeout(timer);
  }, [phase, dismiss]);

  if (phase === "idle") return null;
  const name = call?.other_party_name ?? calleeLabel ?? "Tailora call";
  const status = {
    starting: "Starting call…",
    calling: "Ringing…",
    incoming: "Incoming call",
    connecting: "Connecting…",
    connected: elapsed ?? "Connected",
    ended: message ?? "Call ended.",
  }[phase];

  return (
    <div role="dialog" aria-modal={phase !== "ended"} aria-labelledby="call-heading" aria-describedby="call-status"
      data-call-screen={phase === "ended" ? undefined : ""}
      style={phase === "ended" ? undefined : { backgroundColor: "rgba(28, 34, 48, 0.55)" }}
      className={cn("fixed inset-x-0 z-[2147483100] flex justify-center px-4",
        phase === "ended" ? "bottom-4" : "inset-y-0 items-end pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:items-center sm:pb-0")}>
      <div className="flex w-full max-w-sm flex-col items-center gap-4 rounded-card bg-ink p-6 text-center text-paper shadow-xl">
        <div aria-hidden className="flex size-16 items-center justify-center rounded-full bg-indigo font-display text-2xl">
          {name.slice(0, 1).toUpperCase()}
        </div>
        <div className="flex flex-col gap-1">
          <h2 id="call-heading" ref={headingRef} tabIndex={-1} style={{ outline: "none" }} className="font-display text-2xl">{name}</h2>
          <p id="call-status" role="status" className={cn("text-sm", phase === "connected" ? "font-mono" : "", "text-paper/80")}>{status}</p>
          {call?.order_number && phase !== "ended" && <p className="font-mono text-xs text-paper/60">Order {call.order_number}</p>}
        </div>

        {phase === "incoming" && (
          <div className="flex w-full gap-3">
            <Button variant="danger" className="flex-1" onClick={() => void decline()}>Decline</Button>
            <Button className="flex-1 bg-success text-white hover:bg-success" onClick={() => void answer()}>Answer</Button>
          </div>
        )}
        {(phase === "calling" || phase === "starting" || phase === "connecting" || phase === "connected") && (
          <div className="flex w-full gap-3">
            {phase === "connected" && (
              <Button variant="secondary" className="flex-1" aria-pressed={muted} onClick={() => void toggleMute()}>
                <MicIcon off={muted} />{muted ? "Unmute" : "Mute"}
              </Button>
            )}
            <Button variant="danger" className="flex-1" disabled={phase === "starting"} onClick={() => void hangUp()}>
              {phase === "calling" ? "Cancel" : "Hang up"}
            </Button>
          </div>
        )}
        {phase === "ended" && <Button variant="secondary" size="sm" onClick={dismiss}>Close</Button>}
        {phase !== "ended" && <p className="text-xs text-paper/60">Calls go through Tailora over the internet. Neither of you sees the other's number.</p>}
      </div>
    </div>
  );
}

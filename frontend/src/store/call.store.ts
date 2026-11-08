import { create } from "zustand";
import { callsApi } from "@/api/calls.api";
import { joinVoiceRoom, MicrophoneBlockedError, type VoiceRoom } from "@/lib/calls/voice-room";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { AppCall, AppCallJoin, CallParty } from "@/types/call";

/**
 * One in-app call at a time, shared by every page.
 * Phases: calling (we rang them) -> connected -> ended; or incoming -> connected -> ended.
 */
export type CallPhase = "idle" | "starting" | "calling" | "incoming" | "connecting" | "connected" | "ended";

const ENDED_TEXT: Record<string, string> = {
  declined: "They're busy right now. Try again later or send a message.",
  missed: "No answer. They'll see a missed call.",
  cancelled: "Call cancelled.",
  ended: "Call ended.",
};

interface CallState {
  phase: CallPhase;
  call: AppCall | null;
  /** Who we're calling, before the server has answered. */
  calleeLabel: string | null;
  muted: boolean;
  connectedAt: number | null;
  message: string | null;
  room: VoiceRoom | null;
  start: (orderId: string, party: CallParty, label: string) => Promise<void>;
  ring: (call: AppCall) => void;
  answer: () => Promise<void>;
  decline: () => Promise<void>;
  hangUp: () => Promise<void>;
  toggleMute: () => Promise<void>;
  /** Server says the call changed (polled while ringing either way, and by heartbeats). */
  sync: (call: AppCall) => Promise<void>;
  dismiss: () => void;
  /** Leave any call and forget it, e.g. on sign-out or when the dashboard closes. */
  reset: () => Promise<void>;
}

const HEARTBEAT_MS = 15000;
let pollTimer: ReturnType<typeof setInterval> | null = null;
let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}
function stopHeartbeat() {
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  heartbeatTimer = null;
}

export const useCallStore = create<CallState>((set, get) => {
  async function finish(text: string) {
    stopPolling();
    stopHeartbeat();
    const room = get().room;
    set({ phase: "ended", message: text, room: null, connectedAt: null, muted: false });
    if (room) await room.leave().catch(() => {});
  }

  /** While a call is live, tell the server every 15 s, so a call both people walked away from ends. */
  function startHeartbeat(callId: string) {
    stopHeartbeat();
    heartbeatTimer = setInterval(() => {
      callsApi.heartbeat(callId).then((fresh) => get().sync(fresh)).catch(() => {});
    }, HEARTBEAT_MS);
  }

  /** Poll the server while a call is ringing (either side) for answered / declined / cancelled / missed. */
  function watch(callId: string) {
    stopPolling();
    pollTimer = setInterval(() => {
      callsApi.status(callId).then((fresh) => get().sync(fresh)).catch(() => {});
    }, 2000);
  }

  function markConnected() {
    const call = get().call;
    set((s) => (s.phase === "ended" ? s : { phase: "connected", connectedAt: s.connectedAt ?? Date.now() }));
    if (call && get().phase === "connected" && !heartbeatTimer) startHeartbeat(call.call_id);
  }

  async function join(joined: AppCallJoin) {
    const room = await joinVoiceRoom(joined.url, joined.token, {
      onOtherJoined: () => markConnected(),
      onOtherLeft: () => { void get().hangUp(); },
      onDisconnected: () => { if (get().phase !== "ended") void finish("The call dropped. Check your connection and call again."); },
    });
    if (get().phase === "ended") { await room.leave(); return; }
    set({ room });
  }

  return {
    phase: "idle", call: null, calleeLabel: null, muted: false, connectedAt: null, message: null, room: null,

    async start(orderId, party, label) {
      if (get().phase !== "idle" && get().phase !== "ended") return;
      set({ phase: "starting", call: null, calleeLabel: label, message: null, muted: false });
      let joined: AppCallJoin;
      try {
        joined = await callsApi.startApp(orderId, party);
      } catch (err) {
        set({ phase: "ended", message: getDisplayErrorMessage(err, "The call couldn't be started. Please try again.") });
        return;
      }
      set({ phase: "calling", call: joined });
      try {
        await join(joined);
      } catch (err) {
        await callsApi.cancel(joined.call_id).catch(() => {});
        await finish(err instanceof MicrophoneBlockedError ? err.message : "Couldn't connect the call. Check your connection and try again.");
        return;
      }
      // Watch for them answering, declining or not picking up.
      watch(joined.call_id);
    },

    ring(call) {
      if (get().phase !== "idle" && get().phase !== "ended") return;
      set({ phase: "incoming", call, calleeLabel: null, message: null, muted: false });
      // Stop ringing if the caller gives up or the call times out before we answer.
      watch(call.call_id);
    },

    async answer() {
      const call = get().call;
      if (!call || get().phase !== "incoming") return;
      stopPolling();
      set({ phase: "connecting" });
      try {
        const joined = await callsApi.answer(call.call_id);
        set({ call: joined });
        await join(joined);
        markConnected();
      } catch (err) {
        if (err instanceof MicrophoneBlockedError) {
          await callsApi.end(call.call_id).catch(() => {});
          await finish(err.message);
        } else {
          await finish(getDisplayErrorMessage(err, "This call has ended."));
        }
      }
    },

    async decline() {
      const call = get().call;
      if (!call) return;
      stopPolling();
      await callsApi.decline(call.call_id).catch(() => {});
      set({ phase: "idle", call: null, message: null });
    },

    async hangUp() {
      const { call, phase } = get();
      if (!call || phase === "ended") return;
      if (phase === "calling" || phase === "starting") await callsApi.cancel(call.call_id).catch(() => {});
      else await callsApi.end(call.call_id).catch(() => {});
      await finish(ENDED_TEXT.ended);
    },

    async toggleMute() {
      const { room, muted } = get();
      if (!room) return;
      await room.setMuted(!muted);
      set({ muted: !muted });
    },

    async sync(fresh) {
      const { call, phase } = get();
      if (call?.call_id !== fresh.call_id || phase === "ended" || phase === "idle") return;
      if (fresh.status === "active") {
        if (phase === "incoming") {
          // Answered somewhere else (another tab or device).
          await finish("Answered on another device.");
          return;
        }
        stopPolling();
        set((s) => ({ call: { ...s.call!, ...fresh } }));
        markConnected();
      } else if (fresh.status !== "ringing") {
        if (phase === "incoming") {
          await finish(fresh.status === "cancelled" || fresh.status === "missed" ? `Missed call from ${fresh.other_party_name}.` : ENDED_TEXT.ended);
        } else {
          await finish(ENDED_TEXT[fresh.status] ?? ENDED_TEXT.ended);
        }
      }
    },

    dismiss() {
      stopPolling();
      stopHeartbeat();
      set({ phase: "idle", call: null, calleeLabel: null, message: null, connectedAt: null, muted: false });
    },

    async reset() {
      const { call, phase, room } = get();
      stopPolling();
      stopHeartbeat();
      set({ phase: "idle", call: null, calleeLabel: null, message: null, connectedAt: null, muted: false, room: null });
      if (room) await room.leave().catch(() => {});
      if (!call) return;
      if (phase === "calling" || phase === "starting") await callsApi.cancel(call.call_id).catch(() => {});
      else if (phase === "connected" || phase === "connecting") await callsApi.end(call.call_id).catch(() => {});
    },
  };
});

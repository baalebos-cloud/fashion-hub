/**
 * Push notifications in the phone apps: ask once after sign-in, register this phone with
 * the backend, and open the right page when a notification is tapped.
 * Incoming calls: the backend sends an urgent "Ada is calling" alert (Android: the "calls"
 * channel with its ringtone; iPhone: time-sensitive). Tapping it, or receiving it while the
 * app is open, shows the in-app incoming-call screen; answering still needs a tap there.
 * Needs the Firebase (Android) / APNs (iOS) setup described in docs/mobile-apps.md; without
 * it, registration fails quietly and nothing else changes.
 */
import { apiClient } from "@/lib/api/client";
import { internalPath } from "./app-shell";
import { isNativeApp, nativePlatform } from "./platform";

let registeredToken: string | null = null;
let listening = false;

/** A call alert was tapped or arrived while the app is open: show the call if it's still ringing. */
export async function showCallFromPush(data: Record<string, unknown> | undefined): Promise<void> {
  if (data?.type !== "incoming_call" || typeof data.call_id !== "string") return;
  const [{ callsApi }, { useCallStore }] = await Promise.all([import("@/api/calls.api"), import("@/store/call.store")]);
  try {
    const call = await callsApi.status(data.call_id);
    if (call.status === "ringing" && call.you_are === "callee") useCallStore.getState().ring(call);
  } catch {
    // The call is gone or not ours: nothing to show.
  }
}

export async function registerForPush(navigate: (path: string) => void): Promise<void> {
  if (!isNativeApp()) return;
  const { PushNotifications } = await import("@capacitor/push-notifications");
  if (!listening) {
    listening = true;
    await PushNotifications.addListener("registration", ({ value }) => {
      registeredToken = value;
      void apiClient.post("/devices", { platform: nativePlatform(), token: value }).catch(() => {});
    });
    await PushNotifications.addListener("registrationError", () => {
      // Not configured yet (no Firebase/APNs): the app works without push.
    });
    await PushNotifications.addListener("pushNotificationActionPerformed", ({ notification }) => {
      if (notification.data?.type === "incoming_call") {
        void showCallFromPush(notification.data);
        return;
      }
      const target = typeof notification.data?.url === "string" ? internalPath(notification.data.url) : null;
      if (target) navigate(target);
    });
    // Arriving while the app is open: ring now rather than waiting for the next check.
    await PushNotifications.addListener("pushNotificationReceived", (notification) => {
      void showCallFromPush(notification.data);
    });
  }
  if (nativePlatform() === "android") {
    // Android plays a channel's sound, so calls get their own loud, ringing channel (safe to repeat).
    await PushNotifications.createChannel({
      id: "calls", name: "Incoming calls", description: "Calls from your tailor, vendor, customer or rider",
      importance: 5, visibility: 1, sound: "ringtone.wav", vibration: true, lights: true,
    }).catch(() => {});
  }
  let status = await PushNotifications.checkPermissions();
  if (status.receive === "prompt" || status.receive === "prompt-with-rationale") {
    status = await PushNotifications.requestPermissions();
  }
  if (status.receive === "granted") await PushNotifications.register();
}

/** On sign-out: stop sending this phone notifications for the account that just left. */
export async function unregisterPush(): Promise<void> {
  if (!isNativeApp() || !registeredToken) return;
  const token = registeredToken;
  registeredToken = null;
  await apiClient.delete(`/devices/${encodeURIComponent(token)}`).catch(() => {});
}

/**
 * Push notifications in the phone apps: ask once after sign-in, register this phone with
 * the backend, and open the right page when a notification is tapped. Sending notifications
 * (e.g. ringing for calls when the app is closed) comes in a later phase.
 * Needs the Firebase (Android) / APNs (iOS) setup described in docs/mobile-apps.md; without
 * it, registration fails quietly and nothing else changes.
 */
import { apiClient } from "@/lib/api/client";
import { internalPath } from "./app-shell";
import { isNativeApp, nativePlatform } from "./platform";

let registeredToken: string | null = null;
let listening = false;

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
      const target = typeof notification.data?.url === "string" ? internalPath(notification.data.url) : null;
      if (target) navigate(target);
    });
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

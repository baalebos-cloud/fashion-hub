/**
 * Browser push notification permission + subscription management.
 * Registration of the resulting subscription with the backend (so it can
 * dispatch via backend/app/integrations/notifications/push.py) is left as
 * a TODO here pending a decision on push provider (see PUSH_PROVIDER in
 * backend/.env.example) — this file documents the client-side contract.
 */
export async function requestPushPermission(): Promise<NotificationPermission> {
  if (!("Notification" in window)) return "denied";
  return Notification.requestPermission();
}

export function isPushSupported(): boolean {
  return "Notification" in window && "serviceWorker" in navigator;
}

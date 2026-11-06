/**
 * A random ID for this browser, sent as X-Device-Id so the admin's security view can tell
 * devices apart (websites can't read a device's MAC address). Holds nothing personal.
 */
const KEY = "tailora.device_id";
let memory: string | null = null;

function random(): string {
  const value = globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
  return `web-${value}`;
}

export function getDeviceId(): string {
  if (memory) return memory;
  try {
    const stored = localStorage.getItem(KEY);
    if (stored && /^[A-Za-z0-9-]{8,64}$/.test(stored)) return (memory = stored);
    const fresh = random();
    localStorage.setItem(KEY, fresh);
    return (memory = fresh);
  } catch {
    return (memory = random()); // storage blocked: one ID for this page load
  }
}

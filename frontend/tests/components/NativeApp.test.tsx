import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const native = vi.hoisted(() => ({ on: false, platform: "ios" }));
vi.mock("@capacitor/core", () => ({ Capacitor: { isNativePlatform: () => native.on, getPlatform: () => (native.on ? native.platform : "web") } }));
const vault = vi.hoisted(() => new Map<string, string>());
vi.mock("@aparajita/capacitor-secure-storage", () => ({
  KeychainAccess: { afterFirstUnlockThisDeviceOnly: 3 },
  SecureStorage: {
    setDefaultKeychainAccess: vi.fn(async () => {}), setSynchronize: vi.fn(async () => {}),
    getItem: vi.fn(async (k: string) => vault.get(k) ?? null),
    setItem: vi.fn(async (k: string, v: string) => { vault.set(k, v); }),
    removeItem: vi.fn(async (k: string) => { vault.delete(k); }),
  },
}));
const push = vi.hoisted(() => ({ listeners: {} as Record<string, (e: unknown) => void>, receive: "prompt" }));
vi.mock("@capacitor/push-notifications", () => ({
  PushNotifications: {
    addListener: vi.fn(async (name: string, fn: (e: unknown) => void) => { push.listeners[name] = fn; }),
    checkPermissions: vi.fn(async () => ({ receive: push.receive })),
    requestPermissions: vi.fn(async () => ({ receive: "granted" })),
    register: vi.fn(async () => {}),
    createChannel: vi.fn(async () => {}),
  },
}));
const calls = vi.hoisted(() => ({ status: vi.fn() }));
vi.mock("@/api/calls.api", () => ({ callsApi: { status: calls.status } }));
const ring = vi.hoisted(() => vi.fn());
vi.mock("@/store/call.store", () => ({ useCallStore: { getState: () => ({ ring }) } }));
vi.mock("@/lib/api/client", () => ({ apiClient: { post: vi.fn(async () => ({})), delete: vi.fn(async () => ({})) } }));
const appPlugin = vi.hoisted(() => ({ launchUrl: undefined as string | undefined, listeners: {} as Record<string, (e: unknown) => void> }));
vi.mock("@capacitor/app", () => ({ App: {
  addListener: vi.fn(async (name: string, fn: (e: unknown) => void) => { appPlugin.listeners[name] = fn; }),
  getLaunchUrl: vi.fn(async () => (appPlugin.launchUrl ? { url: appPlugin.launchUrl } : undefined)),
  minimizeApp: vi.fn(async () => {}),
} }));
vi.mock("@capacitor/splash-screen", () => ({ SplashScreen: { hide: vi.fn(async () => {}) } }));
vi.mock("@capacitor/status-bar", () => ({ StatusBar: { setStyle: vi.fn(async () => {}), setBackgroundColor: vi.fn(async () => {}) }, Style: { Light: "LIGHT" } }));

import { initNativeShell, internalPath } from "@/lib/native/app-shell";
import { restoreNativeSession } from "@/lib/native/session";
import { clearTokens, getRefreshToken, setTokens } from "@/lib/auth/token";
import { registerForPush, showCallFromPush, unregisterPush } from "@/lib/native/push";
import { apiClient } from "@/lib/api/client";
import { PushNotifications } from "@capacitor/push-notifications";

const flush = () => new Promise((r) => setTimeout(r, 0));
beforeEach(() => { native.on = false; vault.clear(); sessionStorage.clear(); vi.clearAllMocks(); });
afterEach(() => { native.on = false; });

describe("links that open the app", () => {
  it.each([
    ["tailora://app/customer/orders/42", "/app/customer/orders/42"],
    ["tailora://app/delivery?tab=jobs", "/app/delivery?tab=jobs"],
    ["https://tailora.example/app/vendor/orders/9", "/app/vendor/orders/9"],
    ["/app/professional", "/app/professional"],
  ])("%s -> %s", (url, path) => expect(internalPath(url)).toBe(path));

  it.each(["//evil.example/x", "javascript:alert(1)", "notaurl"])("ignores %s", (url) => {
    const path = internalPath(url);
    expect(path === null || (path.startsWith("/") && !path.startsWith("//"))).toBe(true);
  });
});

describe("staying signed in", () => {
  it("keeps tokens in secure storage in the app, and brings them back after a restart", async () => {
    native.on = true;
    setTokens({ accessToken: "a1", refreshToken: "r1" });
    await flush(); await flush();
    expect(vault.get("tailora.refresh_token")).toBe("r1");
    sessionStorage.clear(); // the app was closed
    await restoreNativeSession();
    expect(getRefreshToken()).toBe("r1");
    clearTokens();
    await flush(); await flush();
    expect(vault.size).toBe(0);
  });

  it("leaves the website exactly as before", async () => {
    setTokens({ accessToken: "a1", refreshToken: "r1" });
    await flush();
    expect(vault.size).toBe(0);
    await restoreNativeSession();
    expect(getRefreshToken()).toBe("r1");
  });
});

describe("push registration", () => {
  it("asks once, registers this phone, opens tapped notifications, and unregisters on sign-out", async () => {
    native.on = true;
    native.platform = "android";
    const navigate = vi.fn();
    await registerForPush(navigate);
    expect(PushNotifications.requestPermissions).toHaveBeenCalled();
    expect(PushNotifications.register).toHaveBeenCalled();
    push.listeners.registration({ value: "fcm-token-123456789" });
    expect(apiClient.post).toHaveBeenCalledWith("/devices", { platform: "android", token: "fcm-token-123456789" });
    push.listeners.pushNotificationActionPerformed({ notification: { data: { url: "tailora://app/customer/orders/7" } } });
    expect(navigate).toHaveBeenCalledWith("/app/customer/orders/7");
    await unregisterPush();
    expect(apiClient.delete).toHaveBeenCalledWith("/devices/fcm-token-123456789");
  });

  it("does nothing on the website", async () => {
    await registerForPush(vi.fn());
    expect(PushNotifications.checkPermissions).not.toHaveBeenCalled();
  });
});

describe("opening the app from a link", () => {
  it("goes to the page in the link that started the app, and to later links too", async () => {
    native.on = true;
    native.platform = "android";
    appPlugin.launchUrl = "tailora://app/customer/orders/42";
    const navigate = vi.fn();
    await initNativeShell(navigate);
    expect(navigate).toHaveBeenCalledWith("/app/customer/orders/42");
    appPlugin.listeners.appUrlOpen({ url: "tailora://app/delivery" });
    expect(navigate).toHaveBeenLastCalledWith("/app/delivery");
  });

  it("stays on the start page when the app was opened normally", async () => {
    native.on = true;
    appPlugin.launchUrl = undefined;
    const navigate = vi.fn();
    await initNativeShell(navigate);
    expect(navigate).not.toHaveBeenCalled();
  });
});

describe("ringing alerts", () => {
  const CALL = { call_id: "c1", status: "ringing", order_id: "o1", order_number: "TL-1", other_party_name: "Ada",
    you_are: "callee", started_at: null, answered_at: null };

  it("Android gets a loud 'Incoming calls' channel with the ringtone", async () => {
    native.on = true;
    native.platform = "android";
    await registerForPush(vi.fn());
    expect(PushNotifications.createChannel).toHaveBeenCalledWith(expect.objectContaining({ id: "calls", importance: 5, sound: "ringtone.wav" }));
  });

  it("tapping a call alert shows the incoming call if it's still ringing", async () => {
    calls.status.mockResolvedValueOnce(CALL);
    await showCallFromPush({ type: "incoming_call", call_id: "c1" });
    expect(ring).toHaveBeenCalledWith(CALL);
  });

  it("does nothing for a call that has already ended, or for other alerts", async () => {
    calls.status.mockResolvedValueOnce({ ...CALL, status: "missed" });
    await showCallFromPush({ type: "incoming_call", call_id: "c1" });
    await showCallFromPush({ type: "missed_call", call_id: "c1" });
    expect(ring).not.toHaveBeenCalled();
  });

  it("rings as soon as an alert arrives while the app is open, and opens the call when tapped", async () => {
    native.on = true;
    native.platform = "ios";
    await registerForPush(vi.fn());
    calls.status.mockResolvedValue(CALL);
    push.listeners.pushNotificationReceived({ data: { type: "incoming_call", call_id: "c1" } });
    await flush(); await flush();
    expect(ring).toHaveBeenCalledTimes(1);
    push.listeners.pushNotificationActionPerformed({ notification: { data: { type: "incoming_call", call_id: "c1" } } });
    await flush(); await flush();
    expect(ring).toHaveBeenCalledTimes(2);
  });
});


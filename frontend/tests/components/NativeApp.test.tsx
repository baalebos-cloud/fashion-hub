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
  },
}));
vi.mock("@/lib/api/client", () => ({ apiClient: { post: vi.fn(async () => ({})), delete: vi.fn(async () => ({})) } }));

import { internalPath } from "@/lib/native/app-shell";
import { restoreNativeSession } from "@/lib/native/session";
import { clearTokens, getRefreshToken, setTokens } from "@/lib/auth/token";
import { registerForPush, unregisterPush } from "@/lib/native/push";
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

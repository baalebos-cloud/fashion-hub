import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { attachRequestInterceptors, attachResponseInterceptors } from "@/lib/api/interceptors";
import { getAccessToken, getRefreshToken, setTokens } from "@/lib/auth/token";

function unauthorized(config: InternalAxiosRequestConfig): never {
  throw new AxiosError("Unauthorized", "ERR_BAD_REQUEST", config, undefined, {
    data: {}, status: 401, statusText: "Unauthorized", headers: {}, config,
  });
}

function setup(refreshFails = false) {
  const client = axios.create({ baseURL: "/api/v1", timeout: 500 });
  const refreshClient = axios.create();
  const refresh = vi.fn(async (config: InternalAxiosRequestConfig) => {
    if (refreshFails) unauthorized(config);
    return { data: { access_token: "new-access" }, status: 200, statusText: "OK", headers: {}, config };
  });
  refreshClient.defaults.adapter = refresh;
  vi.spyOn(axios, "create").mockReturnValueOnce(refreshClient);
  attachRequestInterceptors(client);
  attachResponseInterceptors(client);
  client.defaults.adapter = async (config) => {
    if (config.headers.get("Authorization") !== "Bearer new-access") unauthorized(config);
    return { data: { ok: true }, status: 200, statusText: "OK", headers: {}, config };
  };
  return { client, refresh };
}

beforeEach(() => {
  sessionStorage.clear();
  setTokens({ accessToken: "expired", refreshToken: "valid-refresh" });
});
afterEach(() => vi.restoreAllMocks());

describe("session refresh", () => {
  it("shares one refresh across concurrent expired requests", async () => {
    const { client, refresh } = setup();
    const responses = await Promise.all([client.get("/users/me"), client.get("/orders")]);
    expect(responses.every((response) => response.data.ok)).toBe(true);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBe("new-access");
  });
  it("rejects an expired refresh without deadlocking and clears credentials", async () => {
    const { client, refresh } = setup(true);
    const result = await Promise.allSettled([client.get("/users/me"), client.get("/orders")]);
    expect(result.every((entry) => entry.status === "rejected")).toBe(true);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
  it("does not refresh a failed login", async () => {
    const { client, refresh } = setup();
    await expect(client.post("/auth/login", {})).rejects.toMatchObject({ status: 401 });
    expect(refresh).not.toHaveBeenCalled();
  });
});

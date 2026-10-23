import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth/token";
import { toApiError } from "./errors";

export function attachRequestInterceptors(client: AxiosInstance): void {
  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) config.headers.set("Authorization", `Bearer ${token}`);
    return config;
  });
}

/** Collapse concurrent 401s into one refresh. The refresh transport deliberately
 * has no response interceptor: a rejected refresh must settle, not await itself.
 */
export function attachResponseInterceptors(client: AxiosInstance): void {
  const refreshClient = axios.create({
    baseURL: client.defaults.baseURL,
    timeout: client.defaults.timeout,
    withCredentials: client.defaults.withCredentials,
  });
  let refreshPromise: Promise<string> | null = null;

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const request = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
      const isAuthRequest = /\/auth\/(login|signup|refresh|logout|forgot-password|reset-password|verify-email)(?:[/?]|$)/.test(request?.url ?? "");
      if (error.response?.status !== 401 || !request || request._retry || isAuthRequest) {
        return Promise.reject(toApiError(error));
      }
      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        return Promise.reject(toApiError(error));
      }
      request._retry = true;
      if (!refreshPromise) {
        refreshPromise = refreshClient.post<{ access_token: string; refresh_token: string }>("/auth/refresh", {
          refresh_token: refreshToken,
        }).then(({ data }) => {
          if (typeof data.access_token !== "string" || !data.access_token ||
              typeof data.refresh_token !== "string" || !data.refresh_token) {
            throw new Error("Invalid refresh response");
          }
          if (getRefreshToken() !== refreshToken) throw new Error("Session changed during refresh");
          setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
          return data.access_token;
        }).catch((refreshError: unknown) => {
          if (getRefreshToken() === refreshToken) clearTokens();
          throw refreshError;
        }).finally(() => {
          refreshPromise = null;
        });
      }
      try {
        const token = await refreshPromise;
        request.headers.set("Authorization", `Bearer ${token}`);
        return client(request);
      } catch {
        return Promise.reject(toApiError(error));
      }
    },
  );
}

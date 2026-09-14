import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth/token";
import { toApiError } from "./errors";

/** Attaches the current access token to every outgoing request, if present. */
export function attachRequestInterceptors(client: AxiosInstance): void {
  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      config.headers.set("Authorization", `Bearer ${token}`);
    }
    return config;
  });
}

/**
 * On a 401, attempts exactly one silent refresh-and-retry before giving up
 * and clearing the session. `isRefreshing`/`pendingQueue` collapse
 * concurrent 401s (e.g. five parallel requests firing at once) into a
 * single refresh call rather than hammering /auth/refresh five times.
 */
let isRefreshing = false;
let pendingQueue: Array<(token: string | null) => void> = [];

function resolveQueue(token: string | null) {
  pendingQueue.forEach((resolve) => resolve(token));
  pendingQueue = [];
}

export function attachResponseInterceptors(client: AxiosInstance): void {
  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

      if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
        return Promise.reject(toApiError(error));
      }

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        return Promise.reject(toApiError(error));
      }

      if (isRefreshing) {
        // A refresh is already in flight — wait for it instead of firing
        // another one, then retry this request with whatever token results.
        return new Promise((resolve, reject) => {
          pendingQueue.push((token) => {
            if (!token) return reject(toApiError(error));
            originalRequest._retry = true;
            originalRequest.headers.set("Authorization", `Bearer ${token}`);
            resolve(client(originalRequest));
          });
        });
      }

      isRefreshing = true;
      try {
        const response = await client.post("/auth/refresh", { refresh_token: refreshToken });
        const newAccessToken = response.data.access_token as string;
        setTokens({ accessToken: newAccessToken, refreshToken });
        resolveQueue(newAccessToken);

        originalRequest._retry = true;
        originalRequest.headers.set("Authorization", `Bearer ${newAccessToken}`);
        return client(originalRequest);
      } catch (refreshError) {
        clearTokens();
        resolveQueue(null);
        return Promise.reject(toApiError(error));
      } finally {
        isRefreshing = false;
      }
    }
  );
}

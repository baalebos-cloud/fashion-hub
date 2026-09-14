import axios, { type AxiosInstance } from "axios";
import { apiConfig } from "@/config/api.config";
import { attachRequestInterceptors, attachResponseInterceptors } from "./interceptors";

/**
 * The single Axios instance used by every file in src/api/*.api.ts.
 * Nothing outside src/lib/api and src/api should import axios directly —
 * this is what lets us change auth handling, retries, or error shape in
 * exactly one place.
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: apiConfig.baseUrl,
  timeout: apiConfig.timeoutMs,
  withCredentials: apiConfig.withCredentials,
  headers: {
    "Content-Type": "application/json",
  },
});

attachRequestInterceptors(apiClient);
attachResponseInterceptors(apiClient);

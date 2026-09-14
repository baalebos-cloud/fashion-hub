import type { AxiosError } from "axios";
import type { ApiErrorBody } from "@/types/api";

/**
 * Every service/hook in this app catches ApiError, not a raw AxiosError —
 * normalizing here means a component never needs to know whether a
 * failure came from the network, a timeout, or a structured backend error
 * body (see backend/app/core/exceptions.py for the shape this mirrors).
 */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly requestId: string | null;

  constructor(message: string, code: string, status: number | null, requestId: string | null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export function toApiError(error: AxiosError): ApiError {
  if (error.response) {
    const body = error.response.data as Partial<ApiErrorBody> | undefined;
    if (body?.error) {
      return new ApiError(body.error.message, body.error.code, error.response.status, body.error.request_id);
    }
    return new ApiError(
      `Request failed with status ${error.response.status}.`,
      "unknown_error",
      error.response.status,
      null
    );
  }

  if (error.code === "ECONNABORTED") {
    return new ApiError("The request timed out. Please check your connection and try again.", "timeout", null, null);
  }

  return new ApiError("Unable to reach the server. Please check your connection.", "network_error", null, null);
}

/** Type guard for call sites that want to branch on specific error codes,
 * e.g. showing a dedicated "already exists" message on signup. */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

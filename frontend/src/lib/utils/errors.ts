import { isApiError } from "@/lib/api/errors";

/** Converts any caught error into a message safe to show a person —
 * used by components that don't need the full ApiError object, just a
 * string for a toast or inline error banner. */
export function getDisplayErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (isApiError(error)) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}

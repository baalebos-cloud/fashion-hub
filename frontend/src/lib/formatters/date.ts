import { formatDistanceToNow, parseISO } from "date-fns";
import { formatInTimeZone, toZonedTime } from "date-fns-tz";

/**
 * Single source of truth for turning a backend timestamp into something a
 * person reads. The backend ALWAYS sends UTC ISO-8601 strings (see
 * backend/docs/database.md — "Use server-generated timestamps"); every
 * place in this app that shows a date/time must go through here or
 * hooks/use-timezone.ts, never format a raw string inline.
 */

export function parseServerTimestamp(value: string): Date {
  return parseISO(value);
}

/** e.g. "12 Sep 2026" */
export function formatDate(value: string, timeZone: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, "d MMM yyyy");
}

/** e.g. "12 Sep 2026, 3:45 PM" */
export function formatDateTime(value: string, timeZone: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, "d MMM yyyy, h:mm a");
}

/** e.g. "2 hours ago" — used for notifications, messages, timelines. */
export function formatRelativeTime(value: string): string {
  return formatDistanceToNow(parseServerTimestamp(value), { addSuffix: true });
}

/** For <input type="date"> fields, always local-timezone. */
export function toDateInputValue(value: string, timeZone: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, "yyyy-MM-dd");
}

/** Converts a UTC ISO string to a Date object already shifted into the
 * given timezone, for any consumer (e.g. a calendar widget) that needs a
 * real Date rather than a formatted string. */
export function toZonedDate(value: string, timeZone: string): Date {
  return toZonedTime(parseServerTimestamp(value), timeZone);
}

/** Escape hatch for a custom date-fns format string, still routed through
 * the same timezone-aware path as everything else. */
export function formatWithPattern(value: string, timeZone: string, pattern: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, pattern);
}

/** Non-timezone-aware formatting, only for durations/spans that are
 * already timezone-neutral (e.g. "3 day turnaround"). */
export function formatDuration(days: number): string {
  if (days === 1) return "1 day";
  return `${days} days`;
}

import { formatInTimeZone } from "date-fns-tz";
import { parseServerTimestamp } from "./date";

/** e.g. "3:45 PM" — used where the date is already obvious from context
 * (e.g. grouped-by-day message threads). */
export function formatTime(value: string, timeZone: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, "h:mm a");
}

/** e.g. "15:45" for contexts that prefer 24-hour time (delivery partner
 * operational views tend to). */
export function formatTime24h(value: string, timeZone: string): string {
  return formatInTimeZone(parseServerTimestamp(value), timeZone, "HH:mm");
}

/** Renders an ETA in minutes as "5 min" / "1 hr 20 min", used by tracking
 * components (TrackingMap, EstimatedDelivery). */
export function formatEtaMinutes(etaMinutes: number): string {
  if (etaMinutes < 60) return `${Math.max(0, Math.round(etaMinutes))} min`;
  const hours = Math.floor(etaMinutes / 60);
  const minutes = Math.round(etaMinutes % 60);
  return minutes > 0 ? `${hours} hr ${minutes} min` : `${hours} hr`;
}

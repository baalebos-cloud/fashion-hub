import { useTimezone } from "@/hooks/use-timezone";
import { formatDate, formatDateTime, formatRelativeTime } from "@/lib/formatters/date";
import { formatTime } from "@/lib/formatters/time";

export type DateTimeDisplayFormat = "date" | "time" | "datetime" | "relative";

export interface DateTimeDisplayProps {
  /** A UTC ISO-8601 string, exactly as the backend sends it. Never pass a
   * pre-formatted string or a client-constructed Date here — see
   * backend/docs/database.md: the server is the only source of truth for
   * "when," and this component is the only place that turns it into
   * something a person reads. */
  value: string;
  format?: DateTimeDisplayFormat;
  className?: string;
}

/**
 * THE global timestamp component, per the project's UI architecture
 * requirement. Every screen that shows a date or time — order timelines,
 * invoices, messages, notifications, delivery ETAs — renders it through
 * this component (or, for raw values, through lib/formatters/date.ts +
 * hooks/use-timezone.ts directly) rather than calling `new Date()` or
 * `.toLocaleString()` ad hoc in a page component.
 *
 * Wraps the result in a native <time> element with a machine-readable
 * `dateTime` attribute (still UTC) for accessibility/SEO, while the
 * visible text is in the viewer's own timezone (see useTimezone).
 */
export function DateTimeDisplay({ value, format = "datetime", className }: DateTimeDisplayProps) {
  const timeZone = useTimezone();

  const text = {
    date: () => formatDate(value, timeZone),
    time: () => formatTime(value, timeZone),
    datetime: () => formatDateTime(value, timeZone),
    relative: () => formatRelativeTime(value),
  }[format]();

  return (
    <time dateTime={value} className={className} title={formatDateTime(value, timeZone)}>
      {text}
    </time>
  );
}

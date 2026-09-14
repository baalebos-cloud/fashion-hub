import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime } from "@/lib/formatters/date";

describe("date formatters", () => {
  it("formats a UTC timestamp into the given timezone", () => {
    // 2026-01-15T23:30:00Z is 2026-01-16 in a UTC+2 timezone.
    const value = "2026-01-15T23:30:00Z";
    expect(formatDate(value, "Africa/Lagos")).toBe("16 Jan 2026");
  });

  it("formats date and time together", () => {
    const value = "2026-01-15T12:00:00Z";
    expect(formatDateTime(value, "UTC")).toBe("15 Jan 2026, 12:00 PM");
  });
});

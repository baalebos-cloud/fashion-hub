import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";

describe("<DateTimeDisplay />", () => {
  it("renders a <time> element with the raw UTC value in dateTime", () => {
    render(<DateTimeDisplay value="2026-01-15T12:00:00Z" format="date" />);
    const el = screen.getByText(/2026/);
    expect(el.tagName.toLowerCase()).toBe("time");
    expect(el.getAttribute("dateTime")).toBe("2026-01-15T12:00:00Z");
  });
});

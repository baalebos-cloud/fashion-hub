import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RiderRoute } from "@/components/delivery/RiderRoute";
import { routeSummary, type PlannedRoute } from "@/lib/utils/planned-route";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn() } }));
afterEach(cleanup);

const route: PlannedRoute = {
  id: "b1", total_minutes: 74, baseline_minutes: 110, minutes_saved: 36, solver: "exact_dp", estimated: true, planned_at: null,
  stops: [
    { key: "d1:pickup", kind: "pickup", eta_minutes: 6, load_after: 1, order_number: "CO-1", delivery_id: "d1" },
    { key: "d2:pickup", kind: "pickup", eta_minutes: 15, load_after: 2, order_number: "CO-2", delivery_id: "d2" },
    { key: "d1:dropoff", kind: "dropoff", eta_minutes: 40, load_after: 1, order_number: "CO-1", delivery_id: "d1" },
  ],
};

describe("rider route", () => {
  it("lists stops in order, links each to its own delivery and flags estimates", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: route });
    render(<MemoryRouter><RiderRoute /></MemoryRouter>);
    const first = await screen.findByRole("link", { name: "Collect CO-1" });
    expect(first.getAttribute("href")).toBe("/app/delivery/d1/pickup");
    expect(screen.getByRole("link", { name: "Deliver CO-1" }).getAttribute("href")).toBe("/app/delivery/d1/dropoff");
    expect(screen.getByText(/36 min less than one order at a time/)).toBeTruthy();
    expect(routeSummary(route)).toContain("Times are estimates");
  });

  it("shows nothing with a single delivery", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: null });
    const { container } = render(<MemoryRouter><RiderRoute /></MemoryRouter>);
    await new Promise((r) => setTimeout(r, 0));
    expect(container.textContent).toBe("");
  });
});

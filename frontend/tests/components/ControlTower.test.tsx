import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ControlTower } from "@/components/dispatch/ControlTower";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn() } }));
afterEach(cleanup);

describe("control tower", () => {
  it("shows urgent problems with what to do, riders and today's numbers", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => (url.includes("overview") ? { data: [
      { id: "p1", first_name: "Sola", vehicle_type: "bike", rating: 4.6, state: "on_delivery", active_jobs: 2, tracking: { state: "live", age_seconds: 9 } },
      { id: "p2", first_name: "Ada", vehicle_type: "car", rating: 0, state: "offline", active_jobs: 0, tracking: null },
    ] } : { data: {
      exceptions: [{ type: "dropoff_delayed", severity: "critical", order_number: "CO-9", rider: "Sola", minutes: 80,
        message: "On the road 80 min; expected about 30 min.", action: "Check the rider's location and call them or the customer.",
        delivery_id: "d1", request_id: "r1" }],
      performance: { jobs_requested: 12, delivered: 9, median_minutes_to_assign: 4, median_minutes_to_pickup: 18,
        median_trip_minutes: 31, auto_offer_acceptance: 0.75, auto_offers_answered: 8 },
    } }) as never);
    render(<ControlTower />);
    expect(await screen.findByText("Late delivery · CO-9 · Sola")).toBeTruthy();
    expect(screen.getByText(/expected about 30 min/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: /Riders/ }));
    expect(screen.getByText(/On 2 deliveries · Live · updated 9s ago/)).toBeTruthy();
    expect(screen.getByText("Offline")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Today" }));
    expect(screen.getByText("75% of 8")).toBeTruthy();
    expect(screen.getByText("31 min")).toBeTruthy();
  });
});

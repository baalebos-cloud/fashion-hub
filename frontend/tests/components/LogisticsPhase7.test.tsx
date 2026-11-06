import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { DispatchTripCard } from "@/components/delivery/DispatchTripCard";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";

vi.mock("@/components/calls/CallButton", () => ({ CallButton: () => null }));
vi.mock("@/api/delivery-requests.api", () => ({ deliveryRequestsApi: { journey: vi.fn() } }));
afterEach(cleanup);

const stop = { address: "14 Admiralty Way", latitude: 6.45, longitude: 3.47, contact_name: "Ada", can_call: false };

describe("rider trip card", () => {
  it("shows the LGA, landmark, bus stop and note for the drop-off", () => {
    render(<DispatchTripCard trip={{
      id: "d1", order_id: "o1", status: "in_transit", delivery_fee: 2000, straight_line_km: 3.2, distance_source: "haversine",
      pickup: { ...stop, address: "Yaba workshop" },
      dropoff: { ...stop, lga: "Eti-Osa", landmark: "Opposite the blue mosque", nearest_bus_stop: "Jakande bus stop",
        delivery_instructions: "Call at the gate" },
    }} />);
    expect(screen.getByText("Eti-Osa")).toBeTruthy();
    expect(screen.getByText("Opposite the blue mosque")).toBeTruthy();
    expect(screen.getByText("Jakande bus stop")).toBeTruthy();
    expect(screen.getByText("Note: Call at the gate")).toBeTruthy();
  });
});

describe("delivery journey", () => {
  it("lists the materials trips feeding a customer order", async () => {
    vi.mocked(deliveryRequestsApi.journey).mockResolvedValue({
      order_id: "o1", tracking_number: "CO-1", status: "in_production", delivery_status: null, live: null,
      milestones: [{ key: "placed", label: "Order placed", at: null, state: "done" }],
      materials_legs: [{ order_id: "v1", vendor_name: "Balogun Fabrics", status: "in_transit",
        label: "Materials on their way to your tailor", done: false, updated_at: null }],
    });
    render(<DeliveryJourney orderId="o1" />);
    expect(await screen.findByText("Materials on their way to your tailor")).toBeTruthy();
    expect(screen.getByText(/From Balogun Fabrics/)).toBeTruthy();
  });
});

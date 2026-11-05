import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DeliveryRequests from "@/pages/delivery/DeliveryRequests";
import { DispatchOffers } from "@/components/dispatch/DispatchOffers";
import { DeliveryJourney } from "@/components/dispatch/DeliveryJourney";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import type { DispatchJob } from "@/types/dispatch";

vi.mock("@/api/delivery-requests.api", () => ({
  deliveryRequestsApi: { available: vi.fn(), accept: vi.fn(), makeOffer: vi.fn(), withdrawOffer: vi.fn(),
    sellerDispatch: vi.fn(), acceptOffer: vi.fn(), journey: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback = "error") => (err instanceof Error ? err.message : fallback),
}));
const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({ ...(await orig<typeof import("react-router-dom")>()), useNavigate: () => navigate }));

const soon = new Date(Date.now() + 8 * 60_000).toISOString();
const job: DispatchJob = {
  id: "r1", order_id: "o1", status: "requested", suggested_fare: 3600, currency: "NGN",
  offer_min: 2900, offer_max: 7200, approx_road_km: 20.5, pickup_area: "Ikeja, Lagos",
  dropoff_area: "Victoria Island, Lagos", posted_at: new Date().toISOString(), my_offer: null,
};

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("rider job board", () => {
  it("shows fare, distance and areas, and claims at the suggested fare", async () => {
    vi.mocked(deliveryRequestsApi.available).mockResolvedValue([job]);
    vi.mocked(deliveryRequestsApi.accept).mockResolvedValue({ id: "d1", order_id: "o1", status: "assigned", delivery_fee: 3600 });
    render(<MemoryRouter><DeliveryRequests /></MemoryRouter>);
    expect(await screen.findByText("₦3,600")).toBeTruthy();
    expect(screen.getByText(/≈ 20.5 km/)).toBeTruthy();
    expect(screen.getByText("Pickup · Ikeja, Lagos")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Accept ₦3,600" }));
    await waitFor(() => expect(navigate).toHaveBeenCalled());
    expect(deliveryRequestsApi.accept).toHaveBeenCalledWith("r1");
  });

  it("validates and sends a counter-offer", async () => {
    vi.mocked(deliveryRequestsApi.available).mockResolvedValue([job]);
    vi.mocked(deliveryRequestsApi.makeOffer).mockResolvedValue({ id: "f1", amount: 4000, status: "pending", eta_to_pickup_minutes: 7, expires_at: soon });
    render(<MemoryRouter><DeliveryRequests /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Offer your fare" }));
    fireEvent.change(screen.getByLabelText("Your fare (₦)"), { target: { value: "9000" } });
    fireEvent.click(screen.getByRole("button", { name: "Send offer" }));
    expect(screen.getByRole("alert").textContent).toBe("Offer between ₦2,900 and ₦7,200.");
    expect(deliveryRequestsApi.makeOffer).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Your fare (₦)"), { target: { value: "4000" } });
    fireEvent.change(screen.getByLabelText("Minutes to pickup"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Send offer" }));
    await waitFor(() => expect(deliveryRequestsApi.makeOffer).toHaveBeenCalledWith("r1", 4000, 7));
  });

  it("shows a pending offer and lets the rider withdraw it", async () => {
    vi.mocked(deliveryRequestsApi.available).mockResolvedValue([{ ...job,
      my_offer: { id: "f1", amount: 4000, status: "pending", eta_to_pickup_minutes: 7, expires_at: soon } }]);
    vi.mocked(deliveryRequestsApi.withdrawOffer).mockResolvedValue();
    render(<MemoryRouter><DeliveryRequests /></MemoryRouter>);
    expect(await screen.findByText(/Your offer of ₦4,000 \(7 min to pickup\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Withdraw offer" }));
    await waitFor(() => expect(deliveryRequestsApi.withdrawOffer).toHaveBeenCalledWith("r1"));
  });
});

describe("seller offers", () => {
  it("lists rider offers with rider cards and accepts one", async () => {
    vi.mocked(deliveryRequestsApi.sellerDispatch).mockResolvedValue({
      request: { id: "r1", status: "requested", suggested_fare: 3600, approx_road_km: 20.5, currency: "NGN" },
      offers: [{ id: "f1", amount: 3600, eta_to_pickup_minutes: 6, expires_at: soon,
        rider: { first_name: "Tayo", is_verified: true, rating: 4.8, vehicle_type: "bike", completed_deliveries: 212, photo_url: null } }],
    });
    vi.mocked(deliveryRequestsApi.acceptOffer).mockResolvedValue({ id: "d1", order_id: "o1", status: "assigned", delivery_fee: 3600 });
    const onAssigned = vi.fn();
    render(<DispatchOffers orderId="o1" onAssigned={onAssigned} />);
    expect(await screen.findByText("Tayo")).toBeTruthy();
    expect(screen.getByText("Motorbike · ★ 4.8 · 212 deliveries")).toBeTruthy();
    expect(screen.getByText(/6 min to pickup/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(onAssigned).toHaveBeenCalled());
    expect(deliveryRequestsApi.acceptOffer).toHaveBeenCalledWith("f1");
  });
});

describe("delivery journey", () => {
  it("shows done, current and upcoming steps with a live ETA", async () => {
    vi.mocked(deliveryRequestsApi.journey).mockResolvedValue({
      order_id: "o1", tracking_number: "TL-20431", status: "out_for_delivery", delivery_status: "in_transit",
      milestones: [
        { key: "placed", label: "Order placed", at: "2026-11-01T10:00:00Z", state: "done" },
        { key: "picked_up", label: "Picked up by rider", at: "2026-11-05T11:00:00Z", state: "done" },
        { key: "delivered", label: "Delivered", at: null, state: "current" },
        { key: "received", label: "Received and confirmed", at: null, state: "upcoming" },
      ],
      live: { eta_minutes: 14, distance_remaining_km: 4.2, basis: "live_gps_estimate", updated_at: null },
    });
    render(<DeliveryJourney orderId="o1" />);
    expect(await screen.findByText("14 min")).toBeTruthy();
    expect(screen.getByText("TL-20431")).toBeTruthy();
    expect(screen.getByText("Delivered").closest("li")?.getAttribute("aria-current")).toBe("step");
    expect(screen.getByText(/Estimate from the rider's live location/)).toBeTruthy();
  });
});

it("ignores a malformed journey response instead of crashing the order page", async () => {
  vi.mocked(deliveryRequestsApi.journey).mockResolvedValue([] as never);
  const { container } = render(<DeliveryJourney orderId="o1" />);
  await waitFor(() => expect(deliveryRequestsApi.journey).toHaveBeenCalled());
  expect(container.textContent).toBe("");
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RequestRiderPanel } from "@/components/dispatch/RequestRiderPanel";
import { VendorPickupLocation } from "@/components/dispatch/VendorPickupLocation";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";
import { vendorsApi } from "@/api/vendors.api";

vi.mock("@/api/delivery-requests.api", () => ({
  deliveryRequestsApi: { requestForOrder: vi.fn(), sellerDispatch: vi.fn(), acceptOffer: vi.fn() },
}));
vi.mock("@/api/vendors.api", () => ({ vendorsApi: { mine: vi.fn(), updateMyLocation: vi.fn() } }));
vi.mock("@/components/checkout/MapLocationPicker", () => ({
  MapLocationPicker: ({ onSelect }: { onSelect: (l: Record<string, unknown>) => void }) => (
    <button type="button" onClick={() => onSelect({ latitude: 7.62, longitude: 5.23, formatted_address: "3 Fajuyi Market",
      city: "Ado-Ekiti", state_region: "Ekiti", country: "Nigeria" })}>Pick on map</button>),
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(deliveryRequestsApi.sellerDispatch).mockResolvedValue({ request: null, offers: [] });
});
afterEach(cleanup);

describe("request a rider for materials", () => {
  it("requests a rider and then shows the offers panel", async () => {
    vi.mocked(deliveryRequestsApi.requestForOrder).mockResolvedValue({ id: "r1", order_id: "o1", status: "requested" });
    render(<MemoryRouter><RequestRiderPanel orderId="o1" pickupSettingsPath="/app/vendor/delivery" /></MemoryRouter>);
    vi.mocked(deliveryRequestsApi.sellerDispatch).mockResolvedValue({
      request: { id: "r1", status: "requested", suggested_fare: 1500, approx_road_km: 4.2, currency: "NGN" }, offers: [] });
    fireEvent.click(screen.getByRole("button", { name: "Request a rider" }));
    expect(await screen.findByText("Finding a rider")).toBeTruthy();
    expect(deliveryRequestsApi.requestForOrder).toHaveBeenCalledWith("o1");
  });

  it("links to pickup settings when the store location is missing", async () => {
    vi.mocked(deliveryRequestsApi.requestForOrder).mockRejectedValue(
      new Error("Set your store pickup location before requesting a rider."));
    render(<MemoryRouter><RequestRiderPanel orderId="o1" pickupSettingsPath="/app/vendor/delivery" /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Request a rider" }));
    const link = await screen.findByRole("link", { name: "Set pickup location" });
    expect(link.getAttribute("href")).toBe("/app/vendor/delivery");
  });
});

describe("vendor pickup location", () => {
  it("asks for a pickup point when none is set and saves the area", async () => {
    vi.mocked(vendorsApi.mine).mockResolvedValue({ id: "v1", user_id: "u1", business_name: "Lace World",
      is_verified: true, average_rating: 0, warehouse_location_id: null });
    vi.mocked(vendorsApi.updateMyLocation).mockResolvedValue({ id: "v1", user_id: "u1", business_name: "Lace World",
      is_verified: true, average_rating: 0, warehouse_location_id: "loc1" });
    render(<VendorPickupLocation />);
    expect(await screen.findByText(/You need this before you can request a rider/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Pick on map" }));
    await waitFor(() => expect(vendorsApi.updateMyLocation).toHaveBeenCalledWith(expect.objectContaining({
      latitude: 7.62, longitude: 5.23, city: "Ado-Ekiti", stateRegion: "Ekiti" })));
    expect(await screen.findByText("Pickup location saved.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Change" })).toBeTruthy();
  });
});

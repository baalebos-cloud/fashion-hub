import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RiderStatusCard } from "@/components/delivery/RiderStatusCard";
import { deliveryPartnersApi, type RiderProfile } from "@/api/delivery-partners.api";
import { formatCurrency } from "@/lib/formatters/currency";

vi.mock("@/api/delivery-partners.api", () => ({
  deliveryPartnersApi: { me: vi.fn(), setAvailability: vi.fn(), saveVehicle: vi.fn(), activeDeliveries: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const rider = (over: Partial<RiderProfile> = {}): RiderProfile => ({
  id: "p1", user_id: "u1", vehicle_type: "bike", is_verified: true, is_available: false, average_rating: 4.8, ...over });
const renderCard = () => render(<MemoryRouter><RiderStatusCard /></MemoryRouter>);

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("rider online switch", () => {
  it("goes online on the server, not just on screen", async () => {
    vi.mocked(deliveryPartnersApi.me).mockResolvedValue(rider());
    vi.mocked(deliveryPartnersApi.setAvailability).mockResolvedValue(rider({ is_available: true }));
    renderCard();
    fireEvent.click(await screen.findByRole("switch", { name: "Go online" }));
    expect(await screen.findByText("You're online")).toBeTruthy();
    expect(deliveryPartnersApi.setAvailability).toHaveBeenCalledWith(true);
    expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe("true");
  });

  it("explains that verification is needed and keeps the switch off", async () => {
    vi.mocked(deliveryPartnersApi.me).mockResolvedValue(rider({ is_verified: false }));
    renderCard();
    const toggle = await screen.findByRole("switch", { name: "Go online" });
    expect((toggle as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("link", { name: "Check verification" })).toBeTruthy();
  });

  it("asks for a vehicle first", async () => {
    vi.mocked(deliveryPartnersApi.me).mockResolvedValue(rider({ vehicle_type: null, is_verified: false }));
    vi.mocked(deliveryPartnersApi.saveVehicle).mockResolvedValue(rider({ is_verified: false }));
    renderCard();
    fireEvent.click(await screen.findByRole("button", { name: "Motorbike" }));
    await waitFor(() => expect(deliveryPartnersApi.saveVehicle).toHaveBeenCalledWith("bike"));
  });

  it("shows the server's reason when going online is refused", async () => {
    vi.mocked(deliveryPartnersApi.me).mockResolvedValue(rider());
    vi.mocked(deliveryPartnersApi.setAvailability).mockRejectedValue(new Error("An active delivery must be completed before going available."));
    renderCard();
    fireEvent.click(await screen.findByRole("switch", { name: "Go online" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/active delivery/);
  });
});

describe("prices", () => {
  it("drops .00 on whole naira but keeps real kobo", () => {
    expect(formatCurrency(86000).replace(/\s/g, "")).toBe("₦86,000");
    expect(formatCurrency(86000.5).replace(/\s/g, "")).toBe("₦86,000.50");
  });
});

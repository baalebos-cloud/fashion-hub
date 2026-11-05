import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import Storefront from "@/pages/public/Storefront";
import { ShareShopCard } from "@/components/storefront/ShareShopCard";
import { RiderCard } from "@/components/delivery/RiderCard";
import { storefrontsApi } from "@/api/storefronts.api";
import type { Storefront as StorefrontData } from "@/types/storefront";

const auth = { user: null as null | { role: string }, isAuthenticated: false };
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => auth }));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));
vi.mock("@/api/storefronts.api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/storefronts.api")>();
  return { ...actual, storefrontsApi: { getPublic: vi.fn(), myLink: vi.fn(), changeHandle: vi.fn() } };
});

const shop: StorefrontData = {
  handle: "kemi-couture", share_url: "https://tailora.app/s/kemi-couture", kind: "tailor",
  professional_id: "pro-1", display_name: "Kemi Couture", bio: "Bespoke agbada.", is_verified: true,
  average_rating: 4.6, review_count: 12, years_experience: 8, accepts_new_orders: true,
  area: "Ikeja, Lagos", member_since: 2025, profile_photo_url: null,
  designs: [{ id: "d1", title: "Wedding agbada", base_price: 85000, currency: "NGN", estimated_turnaround_days: 10 }],
  products: [], portfolio: [],
  reviews: [{ id: "r1", reviewer_first_name: "Ada", score: 5, comment: "Perfect fit.", created_at: "2026-10-01" }],
};

function LocationProbe() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "";
  return <p data-testid="probe">{location.pathname}|{from}</p>;
}

function renderShop(path = "/s/kemi-couture") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/s/:handle" element={<Storefront />} />
        <Route path="*" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = null;
  auth.isAuthenticated = false;
});
afterEach(cleanup);

describe("public storefront", () => {
  it("shows a verified shop's catalogue, area and reviews", async () => {
    vi.mocked(storefrontsApi.getPublic).mockResolvedValue(shop);
    renderShop();
    expect(await screen.findByRole("heading", { name: "Kemi Couture" })).toBeTruthy();
    expect(screen.getByText("Verified")).toBeTruthy();
    expect(screen.getByText(/Ikeja, Lagos/)).toBeTruthy();
    expect(screen.getByText("Wedding agbada")).toBeTruthy();
    expect(screen.getByText("Perfect fit.")).toBeTruthy();
    expect(storefrontsApi.getPublic).toHaveBeenCalledWith("kemi-couture");
  });

  it("sends a signed-out visitor to sign in, then back to the order page", async () => {
    vi.mocked(storefrontsApi.getPublic).mockResolvedValue(shop);
    renderShop();
    fireEvent.click(await screen.findByRole("button", { name: "Order from this shop" }));
    expect(screen.getByTestId("probe").textContent).toBe("/login|/app/customer/professionals/pro-1/order");
  });

  it("does not let a vendor account place a clothing order", async () => {
    auth.user = { role: "vendor" };
    auth.isAuthenticated = true;
    vi.mocked(storefrontsApi.getPublic).mockResolvedValue(shop);
    renderShop();
    const button = await screen.findByRole("button", { name: "Order from this shop" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("explains a missing or unverified shop instead of erroring", async () => {
    vi.mocked(storefrontsApi.getPublic).mockRejectedValue(new Error("Shop not found."));
    renderShop("/s/nobody");
    expect(await screen.findByRole("heading", { name: /isn't available/i })).toBeTruthy();
  });
});

describe("owner share card", () => {
  const link = { handle: "kemi-couture", share_url: "https://tailora.app/s/kemi-couture", is_public: false,
    status_message: "Your link is reserved. It goes live once Tailora verifies your shop." };

  it("shows the link, its status and a WhatsApp share", async () => {
    vi.mocked(storefrontsApi.myLink).mockResolvedValue(link);
    render(<ShareShopCard displayName="Kemi Couture" />);
    expect((await screen.findByTestId("shop-link")).textContent).toBe(link.share_url);
    expect(screen.getByText("Awaiting verification")).toBeTruthy();
    const whatsapp = screen.getByRole("button", { name: "Share to WhatsApp" }).closest("a")!;
    expect(whatsapp.getAttribute("href")).toContain(encodeURIComponent(link.share_url));
  });

  it("validates a new handle before calling the API and surfaces conflicts", async () => {
    vi.mocked(storefrontsApi.myLink).mockResolvedValue(link);
    vi.mocked(storefrontsApi.changeHandle).mockRejectedValue(new Error("That link is already taken. Try another."));
    render(<ShareShopCard />);
    fireEvent.click(await screen.findByRole("button", { name: "Change link" }));
    const input = screen.getByLabelText("Shop link name");
    fireEvent.change(input, { target: { value: "bad--name" } });
    fireEvent.click(screen.getByRole("button", { name: "Save link" }));
    expect(screen.getByRole("alert").textContent).toMatch(/single hyphens/);
    expect(storefrontsApi.changeHandle).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: "Kemi-Lagos" } });
    fireEvent.click(screen.getByRole("button", { name: "Save link" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/already taken/));
    expect(storefrontsApi.changeHandle).toHaveBeenCalledWith("kemi-lagos");
  });
});

describe("rider card", () => {
  it("shows first name, verification and track record only", () => {
    render(<RiderCard delivery={{ id: "d", order_id: "o", status: "in_transit", delivery_fee: 0,
      rider_name: "Sola Adebayo", rider_verified: true, rider_rating: 4.8, rider_vehicle_type: "bike",
      rider_completed_deliveries: 132 }} />);
    expect(screen.getByText("Sola")).toBeTruthy();
    expect(screen.queryByText(/Adebayo/)).toBeNull();
    expect(screen.getByText("Verified")).toBeTruthy();
    expect(screen.getByText("Motorbike · ★ 4.8 · 132 deliveries")).toBeTruthy();
  });
});

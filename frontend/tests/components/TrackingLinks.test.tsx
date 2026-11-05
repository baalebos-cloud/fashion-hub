import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ShareTrackingCard } from "@/components/dispatch/ShareTrackingCard";
import PublicTracking from "@/pages/public/PublicTracking";
import { trackingLinksApi } from "@/api/tracking-links.api";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/api/tracking-links.api", () => ({
  trackingLinksApi: { create: vi.fn(), list: vi.fn(), revoke: vi.fn(), publicView: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const later = new Date(Date.now() + 7 * 864e5).toISOString();
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(trackingLinksApi.list).mockResolvedValue([]);
});
afterEach(cleanup);

describe("share tracking card", () => {
  it("creates a link, shows it once with copy and WhatsApp, and lists it for revoking", async () => {
    vi.mocked(trackingLinksApi.create).mockResolvedValue({ id: "l1", url: "https://tailora.app/track/abc", label: "Mum", expires_at: later });
    render(<ShareTrackingCard orderId="o1" orderNumber="TL-1" />);
    fireEvent.change(screen.getByLabelText(/Who is it for/), { target: { value: "Mum" } });
    vi.mocked(trackingLinksApi.list).mockResolvedValue([{ id: "l1", label: "Mum", created_at: later, expires_at: later,
      active: true, revoked: false, access_count: 2, last_accessed_at: null }]);
    fireEvent.click(screen.getByRole("button", { name: "Create tracking link" }));
    expect((await screen.findByTestId("share-url")).textContent).toBe("https://tailora.app/track/abc");
    expect(trackingLinksApi.create).toHaveBeenCalledWith("o1", "Mum");
    expect(screen.getByRole("link", { name: "Share to WhatsApp" }).getAttribute("href"))
      .toContain(encodeURIComponent("https://tailora.app/track/abc"));
    expect(await screen.findByText(/Viewed 2 times/)).toBeTruthy();
    vi.mocked(trackingLinksApi.revoke).mockResolvedValue();
    fireEvent.click(screen.getByRole("button", { name: "Turn off" }));
    await waitFor(() => expect(trackingLinksApi.revoke).toHaveBeenCalledWith("o1", "l1"));
  });
});

const renderPublic = () => render(
  <MemoryRouter initialEntries={["/track/tok"]}><Routes><Route path="/track/:token" element={<PublicTracking />} /></Routes></MemoryRouter>);

describe("public tracking page", () => {
  it("shows progress, rider and ETA without private details, and hides itself from search", async () => {
    vi.mocked(trackingLinksApi.publicView).mockResolvedValue({
      tracking_number: "TL-20431", seller_name: "Kemi Couture", kind: "garment", status: "out_for_delivery",
      delivery_status: "in_transit", dropoff_area: "Lekki, Lagos", eta_minutes: 12, eta_basis: "live_gps_estimate",
      rider: { first_name: "Sola", vehicle_type: "bike", is_verified: true, rating: 4.8 }, link_expires_at: later,
      milestones: [{ key: "picked_up", label: "Picked up by rider", at: null, state: "done" },
        { key: "delivered", label: "Delivered", at: null, state: "current" }],
    });
    renderPublic();
    expect(await screen.findByText("12 min")).toBeTruthy();
    expect(screen.getByText("Sola")).toBeTruthy();
    expect(screen.getByText(/to Lekki, Lagos/)).toBeTruthy();
    expect(screen.getByText(/needs a 6-digit handover code/)).toBeTruthy();
    expect(document.querySelector('meta[name="robots"]')?.getAttribute("content")).toBe("noindex, nofollow");
  });

  it("explains an expired or revoked link", async () => {
    vi.mocked(trackingLinksApi.publicView).mockRejectedValue(new Error("not found"));
    renderPublic();
    expect(await screen.findByRole("heading", { name: /isn't available/ })).toBeTruthy();
  });
});

describe("review fixes", () => {
  it("clears an open page once the link is turned off (404), instead of showing stale status", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.mocked(trackingLinksApi.publicView).mockResolvedValueOnce({
        tracking_number: "TL-1", seller_name: "Kemi Couture", kind: "garment", status: "out_for_delivery",
        delivery_status: "in_transit", dropoff_area: null, eta_minutes: 9, eta_basis: "live_gps_estimate", rider: null,
        link_expires_at: later, milestones: [] });
      renderPublic();
      expect(await screen.findByText("9 min")).toBeTruthy();
      vi.mocked(trackingLinksApi.publicView).mockRejectedValue(new ApiError("gone", "not_found", 404, null));
      await act(async () => { await vi.advanceTimersByTimeAsync(30_000); });
      expect(screen.getByRole("heading", { name: /isn't available/ })).toBeTruthy();
      expect(screen.queryByText("9 min")).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps existing links manageable after receipt but stops creating new ones", async () => {
    vi.mocked(trackingLinksApi.list).mockResolvedValue([{ id: "l1", label: "Mum", created_at: later, expires_at: later,
      active: true, revoked: false, access_count: 0, last_accessed_at: null }]);
    render(<ShareTrackingCard orderId="o1" orderNumber="TL-1" allowCreate={false} />);
    expect(await screen.findByRole("button", { name: "Turn off" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Create tracking link" })).toBeNull();
  });

  it("hides entirely after receipt when no links are live", async () => {
    const { container } = render(<ShareTrackingCard orderId="o1" orderNumber="TL-1" allowCreate={false} />);
    await waitFor(() => expect(trackingLinksApi.list).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

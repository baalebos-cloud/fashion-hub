import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ReservedJobs } from "@/components/dispatch/ReservedJobs";
import { deliveryRequestsApi } from "@/api/delivery-requests.api";

vi.mock("@/api/delivery-requests.api", () => ({
  deliveryRequestsApi: { reservedForMe: vi.fn(), acceptReserved: vi.fn(), declineReserved: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const reserved = (seconds: number) => ({
  id: "jo1", attempt: 1, expires_at: new Date(Date.now() + seconds * 1000).toISOString(),
  job: { id: "r1", order_id: "o1", status: "requested", suggested_fare: 2400, currency: "NGN", offer_min: 1900,
    offer_max: 4800, approx_road_km: 5.4, pickup_area: "Ikeja, Lagos", dropoff_area: "Yaba, Lagos",
    posted_at: new Date().toISOString(), my_offer: null },
});

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("reserved jobs", () => {
  it("shows a countdown and accepts the reserved job", async () => {
    vi.mocked(deliveryRequestsApi.reservedForMe).mockResolvedValue([reserved(75)]);
    vi.mocked(deliveryRequestsApi.acceptReserved).mockResolvedValue({ id: "d1", order_id: "o1", status: "assigned", delivery_fee: 2400 });
    const onAccepted = vi.fn();
    render(<ReservedJobs onAccepted={onAccepted} />);
    expect(await screen.findByText("Reserved for you")).toBeTruthy();
    expect(screen.getByRole("timer").textContent).toMatch(/^1:1[45]$/);
    expect(screen.getByText(/Ikeja, Lagos → Yaba, Lagos/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Accept ₦2,400" }));
    await waitFor(() => expect(onAccepted).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" })));
    expect(deliveryRequestsApi.acceptReserved).toHaveBeenCalledWith("jo1");
  });

  it("declines and lets the parent refresh", async () => {
    vi.mocked(deliveryRequestsApi.reservedForMe).mockResolvedValue([reserved(30)]);
    vi.mocked(deliveryRequestsApi.declineReserved).mockResolvedValue();
    const onChanged = vi.fn();
    render(<ReservedJobs onAccepted={vi.fn()} onChanged={onChanged} />);
    fireEvent.click(await screen.findByRole("button", { name: "Decline" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(deliveryRequestsApi.declineReserved).toHaveBeenCalledWith("jo1");
  });

  it("renders nothing when auto-offers are off or the window has passed", async () => {
    vi.mocked(deliveryRequestsApi.reservedForMe).mockResolvedValue([reserved(-5)]);
    const { container } = render(<ReservedJobs onAccepted={vi.fn()} />);
    await waitFor(() => expect(deliveryRequestsApi.reservedForMe).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

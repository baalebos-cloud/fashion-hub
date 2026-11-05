import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { OneTimeCode } from "@/components/delivery/OneTimeCode";
import { PickupCodeCard } from "@/components/dispatch/PickupCodeCard";
import { DeliveryEventLog } from "@/components/dispatch/DeliveryEventLog";
import Pickup from "@/pages/delivery/Pickup";
import { deliveriesApi } from "@/api/deliveries.api";
import { adminDispatchApi } from "@/api/admin-dispatch.api";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/api/deliveries.api", () => ({
  newIdempotencyKey: vi.fn(),
  deliveriesApi: { getByOrder: vi.fn(), getPickupCode: vi.fn(), rotatePickupCode: vi.fn(), markPickedUp: vi.fn() },
}));
vi.mock("@/api/admin-dispatch.api", () => ({ adminDispatchApi: { events: vi.fn() } }));
const hookDelivery = { id: "d1", order_id: "o1", status: "assigned", delivery_fee: 2500, pickup_code_required: true };
vi.mock("@/hooks/use-delivery", () => ({
  useDelivery: () => ({ delivery: hookDelivery, isLoading: false, error: null }),
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback?: string) => (err instanceof Error ? err.message : fallback ?? "error"),
}));

const soon = () => new Date(Date.now() + 30 * 60_000).toISOString();
let keyCounter = 0;
beforeEach(async () => {
  vi.clearAllMocks();
  keyCounter = 0;
  const mod = await import("@/api/deliveries.api");
  vi.mocked(mod.newIdempotencyKey).mockImplementation(() => `key-${++keyCounter}`);
});
afterEach(cleanup);

describe("one-time code", () => {
  it("shows the code with its expiry and swaps it for a new one on request", async () => {
    const load = vi.fn().mockResolvedValue({ code: "482913", expiresAt: soon() });
    const rotate = vi.fn().mockResolvedValue({ code: "105577", expiresAt: soon() });
    render(<OneTimeCode label="Handover code" hint="Only after you have the package." load={load} rotate={rotate} />);
    expect((await screen.findByTestId("one-time-code")).textContent).toBe("482913");
    expect(screen.getByText(/Works once\. Expires/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Get a new code" }));
    await waitFor(() => expect(screen.getByTestId("one-time-code").textContent).toBe("105577"));
  });

  it("fetches a fresh code by itself when the shown one lapses", async () => {
    const load = vi.fn()
      .mockResolvedValueOnce({ code: "111111", expiresAt: new Date(Date.now() - 1000).toISOString() })
      .mockResolvedValue({ code: "222222", expiresAt: soon() });
    render(<OneTimeCode label="Pickup code" hint="" load={load} rotate={vi.fn()} />);
    await waitFor(() => expect(screen.getByTestId("one-time-code").textContent).toBe("222222"), { timeout: 3000 });
  });
});

describe("seller pickup code card", () => {
  it("shows the pickup code while the rider is on the way", async () => {
    vi.mocked(deliveriesApi.getByOrder).mockResolvedValue({ id: "d1", order_id: "o1", status: "assigned", delivery_fee: 2500, rider_name: "Sola" });
    vi.mocked(deliveriesApi.getPickupCode).mockResolvedValue({ delivery_id: "d1", required: true, pickup_code: "730155", expires_at: soon() });
    render(<PickupCodeCard orderId="o1" />);
    expect((await screen.findByTestId("one-time-code")).textContent).toBe("730155");
    expect(screen.getByText("Hand over to Sola")).toBeTruthy();
  });

  it("stays hidden once the package is collected", async () => {
    vi.mocked(deliveriesApi.getByOrder).mockResolvedValue({ id: "d1", order_id: "o1", status: "in_transit", delivery_fee: 2500 });
    render(<PickupCodeCard orderId="o1" />);
    await waitFor(() => expect(deliveriesApi.getByOrder).toHaveBeenCalled());
    expect(screen.queryByText(/Pickup code/)).toBeNull();
    expect(deliveriesApi.getPickupCode).not.toHaveBeenCalled();
  });
});

describe("rider pickup", () => {
  const renderPickup = () => render(
    <MemoryRouter initialEntries={["/delivery/d1/pickup"]}>
      <Routes>
        <Route path="/delivery/:deliveryId/pickup" element={<Pickup />} />
        <Route path="*" element={<p>navigated</p>} />
      </Routes>
    </MemoryRouter>);

  it("needs the six-digit code, records the package count and reuses the key on a network retry", async () => {
    renderPickup();
    const confirm = screen.getByRole("button", { name: /picked up the package/ });
    expect((confirm as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Pickup code"), { target: { value: "73a0155" } });
    expect((screen.getByLabelText("Pickup code") as HTMLInputElement).value).toBe("730155");
    fireEvent.click(screen.getByRole("button", { name: "More packages" }));
    expect(screen.getByTestId("package-count").textContent).toBe("2");

    vi.mocked(deliveriesApi.markPickedUp).mockRejectedValueOnce(new ApiError("Network error", "NETWORK", null, null));
    fireEvent.click(confirm);
    expect(await screen.findByRole("alert")).toBeTruthy();
    vi.mocked(deliveriesApi.markPickedUp).mockRejectedValueOnce(new ApiError("Incorrect pickup code.", "VALIDATION_ERROR", 422, null));
    fireEvent.click(confirm);
    expect(await screen.findByText("Incorrect pickup code.")).toBeTruthy();
    vi.mocked(deliveriesApi.markPickedUp).mockResolvedValueOnce({ id: "d1", order_id: "o1", status: "in_transit", delivery_fee: 2500 });
    fireEvent.click(confirm);
    expect(await screen.findByText("navigated")).toBeTruthy();

    const keys = vi.mocked(deliveriesApi.markPickedUp).mock.calls.map((call) => call[2]);
    // Network failure: same key retried. Definite rejection: next attempt gets a new key.
    expect(keys).toEqual(["key-1", "key-1", "key-2"]);
    expect(vi.mocked(deliveriesApi.markPickedUp).mock.calls[0][1]).toEqual({ pickup_code: "730155", package_count: 2 });
  });
});

describe("rider pickup with the code switched off", () => {
  it("lets the rider confirm with just the package count", async () => {
    hookDelivery.pickup_code_required = false;
    try {
      render(<MemoryRouter initialEntries={["/delivery/d1/pickup"]}><Routes>
        <Route path="/delivery/:deliveryId/pickup" element={<Pickup />} />
        <Route path="*" element={<p>navigated</p>} /></Routes></MemoryRouter>);
      expect(screen.queryByLabelText("Pickup code")).toBeNull();
      vi.mocked(deliveriesApi.markPickedUp).mockResolvedValueOnce({ id: "d1", order_id: "o1", status: "in_transit", delivery_fee: 2500 });
      fireEvent.click(screen.getByRole("button", { name: /picked up the package/ }));
      expect(await screen.findByText("navigated")).toBeTruthy();
      expect(vi.mocked(deliveriesApi.markPickedUp).mock.calls[0][1]).toEqual({ package_count: 1 });
    } finally {
      hookDelivery.pickup_code_required = true;
    }
  });
});

describe("admin event log", () => {
  it("lists what happened on a run in plain words", async () => {
    vi.mocked(adminDispatchApi.events).mockResolvedValue([
      { id: "e1", event_type: "pickup_code_issued", actor_role: "tailor", details: { reason: "first" }, created_at: soon() },
      { id: "e2", event_type: "pickup_verification_failed", actor_role: "delivery_partner", details: { reason: "rejected" }, created_at: soon() },
      { id: "e3", event_type: "picked_up", actor_role: "delivery_partner", details: { package_count: 2 }, created_at: soon() },
    ]);
    render(<DeliveryEventLog deliveryId="d1" />);
    fireEvent.click(screen.getByRole("button", { name: "Event log" }));
    expect(await screen.findByText("Package collected · 2 packages")).toBeTruthy();
    expect(screen.getByText("Wrong pickup code entered")).toBeTruthy();
    expect(adminDispatchApi.events).toHaveBeenCalledWith("d1");
  });
});

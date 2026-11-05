import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import VendorOrderDetails from "@/pages/professional/VendorOrderDetails";
import { ordersApi } from "@/api/orders.api";

const order = { id: "o1", order_number: "VO-1", order_type: "vendor_order", status: "in_transit", currency: "NGN",
  total_amount: 12000, subtotal: 12000, items: [], buyer_user_id: "t1", seller_user_id: "v1" };
vi.mock("@/hooks/use-order", () => ({
  useOrder: () => ({ order, timeline: [], isLoading: false, error: null, cancel: vi.fn() }),
}));
vi.mock("@/api/orders.api", () => ({ ordersApi: { getById: vi.fn(), confirmMaterialsReceived: vi.fn() } }));
vi.mock("@/components/dispatch/DeliveryJourney", () => ({ DeliveryJourney: () => null }));
vi.mock("@/components/delivery/CustomerDeliveryTracking", () => ({ CustomerDeliveryTracking: () => null }));
vi.mock("@/components/calls/OrderContacts", () => ({ OrderContacts: () => null }));
vi.mock("@/components/orders/OrderItems", () => ({ OrderItems: () => null }));
vi.mock("@/components/orders/OrderTimeline", () => ({ OrderTimeline: () => null }));

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("materials receipt", () => {
  it("shows the confirm button once the rider delivers, without reloading the page", async () => {
    vi.useFakeTimers();
    vi.mocked(ordersApi.getById).mockResolvedValue({ ...order, status: "delivered" } as never);
    render(<MemoryRouter initialEntries={["/o1"]}><Routes><Route path="/:orderId" element={<VendorOrderDetails />} /></Routes></MemoryRouter>);
    expect(screen.queryByRole("button", { name: "Confirm materials received" })).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(ordersApi.getById).toHaveBeenCalledWith("o1");
    expect(screen.getByRole("button", { name: "Confirm materials received" })).toBeTruthy();
  });
});

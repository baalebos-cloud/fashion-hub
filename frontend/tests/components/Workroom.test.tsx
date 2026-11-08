import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "@/pages/professional/Dashboard";
import Payments from "@/pages/professional/Payments";
import { ordersApi } from "@/api/orders.api";
import { WORKROOM_STAGES } from "@/constants/order-status";
import { CUSTOMER_ORDER_STATUS_LABELS } from "@/constants/order-status";

const { o, ORDERS } = vi.hoisted(() => {
  const o = (id: string, status: string, total: number, extra = {}) => ({
    id, order_number: `TL-${id}`, order_type: "customer_order", status, buyer_user_id: "c1", seller_user_id: "t1",
    total_amount: total, currency: "NGN", items: [{ id: `${id}-i`, name_snapshot: `Garment ${id}`, quantity: 1, line_total: total }],
    accepted_at: new Date().toISOString(), ...extra,
  });
  const ORDERS = [o("1", "paid", 120000), o("2", "in_production", 45000), o("3", "ready_for_delivery", 30000), o("4", "completed", 32000), o("5", "cancelled", 10000)];
  return { o, ORDERS };
});

vi.mock("@/hooks/use-orders", () => ({ useOrders: () => ({ orders: ORDERS, isLoading: false, error: null, refetch: vi.fn() }) }));
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => ({ user: { id: "t1", role: "tailor", full_name: "Kemi Adeyemi" } }) }));
vi.mock("@/components/storefront/ShareShopCard", () => ({ ShareShopCard: () => null }));
vi.mock("@/api/orders.api", () => ({ ordersApi: { list: vi.fn().mockResolvedValue([
  { ...o("m1", "in_transit", 47500), order_type: "vendor_order", buyer_user_id: "t1", seller_user_id: "v1", items: [{ id: "x", name_snapshot: "French lace, royal blue", quantity: 1, line_total: 47500 }] },
]) } }));
afterEach(cleanup);

describe("workroom stages", () => {
  it("cover every live order status exactly once", () => {
    const covered = WORKROOM_STAGES.flatMap((s) => s.statuses);
    expect(new Set(covered).size).toBe(covered.length);
    const live = Object.keys(CUSTOMER_ORDER_STATUS_LABELS).filter((s) => !["cancelled", "rejected", "refunded"].includes(s));
    expect([...covered].sort()).toEqual(live.sort());
  });
});

describe("workroom dashboard", () => {
  it("shows what needs attention, the board by real status, honest money, and material orders", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const attention = screen.getByRole("region", { name: "Needs attention" });
    expect(within(attention).getByText(/1 paid order waiting for you to accept/)).toBeTruthy();
    expect(within(attention).getByText(/1 order ready for a rider/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Review 1 new order" })).toBeTruthy();

    const board = screen.getByRole("region", { name: "Orders by stage" });
    expect(within(board).getByText("Garment 1")).toBeTruthy();
    expect(within(board).getByText("Waiting for you")).toBeTruthy();
    expect(within(board).getByText("Mark ready when it's finished")).toBeTruthy();
    expect(within(board).queryByText("Garment 5")).toBeNull(); // cancelled orders aren't on the board

    const money = screen.getByRole("region", { name: "Money this month" });
    expect(within(money).getByText("₦227,000")).toBeTruthy(); // paid + in production + ready + completed; not cancelled
    expect(within(money).getAllByText("Not yet available")).toHaveLength(3);
    expect(within(money).getByText("Not switched on")).toBeTruthy();

    expect(await screen.findByText("French lace, royal blue")).toBeTruthy();
    expect(ordersApi.list).toHaveBeenCalledWith({ perspective: "buying", order_type: "vendor_order" });
  });
});

describe("payments page", () => {
  it("lists order values without claiming payments succeeded", () => {
    render(<MemoryRouter><Payments /></MemoryRouter>);
    expect(screen.getByText("Payments and payouts not switched on")).toBeTruthy();
    expect(screen.queryByText(/successful/i)).toBeNull();
    expect(screen.queryByText("Garment 5")).toBeNull();
  });
});

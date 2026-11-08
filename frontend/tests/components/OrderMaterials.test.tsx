import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderMaterials } from "@/components/orders/OrderMaterials";
import { ordersApi } from "@/api/orders.api";
import type { Order } from "@/types/order";

vi.mock("@/api/orders.api", () => ({ ordersApi: { listAll: vi.fn(), linkMaterial: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

const order = (id: string, status: string, extra: Partial<Order> = {}) => ({
  id, order_number: `VO-${id}`, order_type: "vendor_order", status, buyer_user_id: "t1", seller_user_id: "v1",
  items: [{ id: `${id}-i`, name_snapshot: `Lace ${id}`, quantity: 1, line_total: 1000 }], subtotal: 1000, delivery_fee: 0,
  tax_amount: 0, discount_amount: 0, total_amount: 1000, currency: "NGN", parent_customer_order_id: null, ...extra,
}) as Order;
const garment = { ...order("g1", "accepted"), order_type: "customer_order", order_number: "TL-1" } as Order;

describe("materials for an order", () => {
  it("lists linked material orders and links an unpaid one", async () => {
    vi.mocked(ordersApi.listAll)
      .mockResolvedValueOnce([order("a", "paid", { parent_customer_order_id: "g1" }), order("b", "checkout"), order("c", "paid"), order("d", "checkout", { parent_customer_order_id: "other" })])
      .mockResolvedValueOnce([order("a", "paid", { parent_customer_order_id: "g1" }), order("b", "checkout", { parent_customer_order_id: "g1" })]);
    vi.mocked(ordersApi.linkMaterial).mockResolvedValue(order("b", "checkout", { parent_customer_order_id: "g1" }));
    render(<MemoryRouter><OrderMaterials order={garment} /></MemoryRouter>);
    const panel = screen.getByRole("region", { name: "Materials for this order" });
    expect(await within(panel).findByText("Lace a")).toBeTruthy();
    const select = within(panel).getByLabelText(/Link a material order/) as HTMLSelectElement;
    // Only unpaid, unlinked purchases can be linked.
    expect([...select.options].map((o) => o.value)).toEqual(["", "b"]);
    fireEvent.change(select, { target: { value: "b" } });
    fireEvent.click(within(panel).getByRole("button", { name: "Link" }));
    await waitFor(() => expect(ordersApi.linkMaterial).toHaveBeenCalledWith("g1", "b"));
    expect(await within(panel).findByText("Lace b")).toBeTruthy();
  });

  it("offers no linking once the garment is past production", async () => {
    vi.mocked(ordersApi.listAll).mockResolvedValue([order("b", "checkout")]);
    render(<MemoryRouter><OrderMaterials order={{ ...garment, status: "ready_for_delivery" }} /></MemoryRouter>);
    expect(await screen.findByText("No material orders linked yet.")).toBeTruthy();
    expect(screen.queryByLabelText(/Link a material order/)).toBeNull();
  });
});

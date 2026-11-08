import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Dashboard from "@/pages/vendor/Dashboard";
import Orders from "@/pages/vendor/Orders";
import OrderDetails from "@/pages/vendor/OrderDetails";
import Inventory from "@/pages/vendor/Inventory";
import AddProduct from "@/pages/vendor/AddProduct";
import Payments from "@/pages/vendor/Payments";
import { inventoryApi } from "@/api/inventory.api";
import { productsApi } from "@/api/products.api";
import { vendorsApi } from "@/api/vendors.api";
import { VENDOR_ORDER_GROUPS, VENDOR_ORDER_STATUS_LABELS } from "@/constants/order-status";

const { vo, ORDERS, STOCK, orderState } = vi.hoisted(() => {
  const now = new Date().toISOString();
  const vo = (id: string, status: string, total: number, name = `Fabric ${id}`) => ({
    id, order_number: `VO-${id}`, order_type: "vendor_order", status, buyer_user_id: "t1", seller_user_id: "v1",
    total_amount: total, currency: "NGN", items: [{ id: `${id}-i`, name_snapshot: name, quantity: 5, line_total: total }],
    ordered_at: now, paid_at: now,
  });
  const ORDERS = [
    vo("1", "paid", 47500, "French lace, royal blue"), vo("2", "paid", 30000), vo("3", "processing", 12000),
    vo("4", "ready_for_pickup", 9000), vo("5", "in_transit", 20000), vo("6", "completed", 15000), vo("7", "cancelled", 99000),
  ];
  const STOCK = [
    { id: "s1", product_variant_id: "pv1", product_name: "Ankara print", sku: "ANK-1", quantity_available: 40, quantity_reserved: 0 },
    { id: "s2", product_variant_id: "pv2", product_name: "Aso oke, wine", sku: "ASO-W", quantity_available: 0, quantity_reserved: 2 },
    { id: "s3", product_variant_id: "pv3", product_name: "French lace, royal blue", sku: "FL-RB", quantity_available: 6, quantity_reserved: 5 },
  ];
  const orderState = { status: "paid" };
  return { vo, ORDERS, STOCK, orderState };
});

vi.mock("@/api/orders.api", () => ({ ordersApi: { listAll: vi.fn(() => Promise.resolve(ORDERS)) } }));
vi.mock("@/api/inventory.api", () => ({ inventoryApi: { listAll: vi.fn(() => Promise.resolve(STOCK)), restock: vi.fn() } }));
vi.mock("@/api/products.api", () => ({ productsApi: { create: vi.fn() } }));
vi.mock("@/api/vendors.api", () => ({ vendorsApi: { mine: vi.fn(async () => ({ low_stock_threshold: 10 })), setStockAlert: vi.fn() } }));
vi.mock("@/lib/storage/file-storage", () => ({ uploadFile: vi.fn().mockResolvedValue({ url: "https://cdn.example/lace.jpg" }) }));
vi.mock("@/hooks/use-auth", () => ({ useAuth: () => ({ user: { id: "v1", role: "vendor", full_name: "Lagos Fabrics" } }) }));
vi.mock("@/components/storefront/ShareShopCard", () => ({ ShareShopCard: () => null }));
vi.mock("@/components/calls/OrderContacts", () => ({ OrderContacts: () => null }));
vi.mock("@/components/dispatch/RequestRiderPanel", () => ({ RequestRiderPanel: () => <p>request rider panel</p> }));
vi.mock("@/components/dispatch/PickupCodeCard", () => ({ PickupCodeCard: () => null }));
vi.mock("@/components/dispatch/DeliveryJourney", () => ({ DeliveryJourney: () => null }));
const vendorFulfillment = vi.fn();
vi.mock("@/hooks/use-order", () => ({
  useOrder: () => ({ order: { ...vo("1", orderState.status, 47500, "French lace, royal blue") }, timeline: [], isLoading: false, error: null, vendorFulfillment }),
}));

beforeEach(() => { vi.clearAllMocks(); orderState.status = "paid"; });
afterEach(cleanup);
const inRouter = (ui: React.ReactNode) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe("vendor order groups", () => {
  it("cover every sold vendor status exactly once", () => {
    const covered = VENDOR_ORDER_GROUPS.flatMap((g) => g.statuses);
    expect(new Set(covered).size).toBe(covered.length);
    const sold = Object.keys(VENDOR_ORDER_STATUS_LABELS).filter((s) => !["cart", "checkout", "payment_pending"].includes(s));
    expect([...covered].sort()).toEqual(sold.sort());
  });
});

describe("vendor today", () => {
  it("counts work by stage, lists open orders, flags low stock and shows sales without claiming payouts", async () => {
    inRouter(<Dashboard />);
    const glance = await screen.findByRole("region", { name: "At a glance" });
    expect(within(glance).getByText("New orders").nextSibling?.textContent).toBe("2");
    expect(within(glance).getByText("To prepare").nextSibling?.textContent).toBe("1");
    expect(within(glance).getByText("Waiting for pickup").nextSibling?.textContent).toBe("1");
    expect(within(glance).getByText("On the road").nextSibling?.textContent).toBe("1");
    expect(screen.getByRole("link", { name: "Confirm 2 new orders" })).toBeTruthy();

    const handle = screen.getByRole("region", { name: "Orders to handle" });
    expect(within(handle).getByText("French lace, royal blue × 5")).toBeTruthy();
    expect(within(handle).queryByText(/Fabric 6/)).toBeNull(); // completed isn't open work
    expect(within(handle).queryByText(/Fabric 7/)).toBeNull(); // nor cancelled

    const low = screen.getByRole("region", { name: "Low on stock" });
    expect(await within(low).findByText("Aso oke, wine")).toBeTruthy();
    expect(within(low).getByText("Out")).toBeTruthy();
    expect(within(low).getByText("French lace, royal blue")).toBeTruthy();
    expect(within(low).queryByText("Ankara print")).toBeNull();

    const sales = screen.getByRole("region", { name: "Sales this month" });
    expect(within(sales).getByText("₦133,500")).toBeTruthy(); // every paid order except the cancelled one
    expect(within(sales).getByText("Payouts not switched on")).toBeTruthy();
  });
});

describe("vendor orders", () => {
  it("opens on orders to confirm and switches groups", async () => {
    inRouter(<Orders />);
    expect(await screen.findByRole("tab", { name: /To confirm\s*2/ })).toBeTruthy();
    expect(screen.getByRole("tab", { name: /To confirm/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByText("French lace, royal blue × 5")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: /On the road/ }));
    expect(screen.getByText("Fabric 5 × 5")).toBeTruthy();
    expect(screen.queryByText("French lace, royal blue × 5")).toBeNull();
  });
});

describe("vendor order page", () => {
  const renderOrder = () => render(
    <MemoryRouter initialEntries={["/app/vendor/orders/1"]}>
      <Routes><Route path="/app/vendor/orders/:orderId" element={<OrderDetails />} /></Routes>
    </MemoryRouter>);

  it("shows progress and the one next action, and is honest about declining", async () => {
    renderOrder();
    const progress = screen.getByRole("list", { name: "Fulfilment progress" });
    expect(within(progress).getByText("Order received").closest("li")?.getAttribute("aria-current")).toBe("step");
    const next = screen.getByRole("region", { name: "Next step" });
    expect(within(next).getByText("Confirm you have it")).toBeTruthy();
    expect(within(next).getByText(/refunds, which aren't switched on/)).toBeTruthy();
    fireEvent.click(within(next).getByRole("button", { name: "Confirm and start preparing" }));
    await waitFor(() => expect(vendorFulfillment).toHaveBeenCalledWith("confirmed"));
  });

  it("offers the rider request once it's ready for pickup", () => {
    orderState.status = "ready_for_pickup";
    renderOrder();
    expect(screen.getByText("request rider panel")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Next step" })).queryByRole("button")).toBeNull();
  });
});

describe("vendor inventory", () => {
  it("lists lowest stock first, filters to low, and restocks with a reused key on retry", async () => {
    vi.mocked(inventoryApi.restock)
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce({ ...STOCK[1], quantity_available: 12 });
    inRouter(<Inventory />);
    const items = await screen.findAllByRole("listitem");
    expect(items.map((li) => within(li).getAllByText(/./)[0].textContent)).toEqual(["Aso oke, wine", "French lace, royal blue", "Ankara print"]);
    expect(within(items[0]).getByText("Out of stock")).toBeTruthy();
    expect(within(items[1]).getByText("Low")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Low or out/ }));
    expect(screen.queryByText("Ankara print")).toBeNull();

    fireEvent.change(screen.getByLabelText("Add to stock", { selector: "#restock-s2" }), { target: { value: "12" } });
    const restock = within(screen.getAllByRole("listitem")[0]).getByRole("button", { name: "Restock" });
    fireEvent.click(restock);
    expect(await screen.findByText("Network error")).toBeTruthy();
    fireEvent.click(restock);
    expect(await screen.findByText("Added 12.")).toBeTruthy();
    const calls = vi.mocked(inventoryApi.restock).mock.calls;
    expect(calls[0][0]).toBe("pv2");
    expect(calls[0][1]).toBe(12);
    expect(calls[1][2]).toBe(calls[0][2]); // same idempotency key, so stock can't be added twice
  });
});

describe("add product", () => {
  it("lists what's missing, previews the listing and sends the same request as before", async () => {
    vi.mocked(productsApi.create).mockResolvedValue({ id: "p1" } as never);
    inRouter(<AddProduct />);
    expect(screen.getByText(/3 things to do before you can list it: add a product name, set a price, add at least one photo/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Add product" }) as HTMLButtonElement).disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "French lace, royal blue" } });
    fireEvent.change(screen.getByLabelText("Price per yard (₦)"), { target: { value: "9500" } });
    fireEvent.change(screen.getByLabelText("In stock (yards)"), { target: { value: "30" } });
    const file = new File(["x"], "lace.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Material photos (1–5)"), { target: { files: [file] } });
    expect(await screen.findByAltText("Material photo 1")).toBeTruthy();
    expect(screen.queryByText(/to do before you can list it/)).toBeNull();

    const preview = screen.getByRole("complementary", { name: "How tailors will see it" });
    expect(within(preview).getByText("₦9,500 / yard")).toBeTruthy();
    expect(within(preview).getByText("In stock")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Add product" }));
    await waitFor(() => expect(productsApi.create).toHaveBeenCalledWith({
      name: "French lace, royal blue", description: "", base_price: 9500, initial_stock: 30,
      image_urls: ["https://cdn.example/lace.jpg"], unit_of_measure: "yard",
    }));
  });
});

describe("vendor payments", () => {
  it("lists paid order values and never claims a payout", async () => {
    inRouter(<Payments />);
    expect(await screen.findByText(/6 orders · total value/)).toBeTruthy();
    expect(screen.getByText("₦133,500")).toBeTruthy();
    expect(screen.getByText("Payouts not switched on")).toBeTruthy();
    expect(screen.queryByText(/received|paid out|successful/i)).toBeNull();
  });
});

describe("low stock alert level", () => {
  it("uses the vendor's own level and lets them change it", async () => {
    vi.mocked(vendorsApi.mine).mockResolvedValueOnce({ low_stock_threshold: 5 } as never);
    vi.mocked(vendorsApi.setStockAlert).mockResolvedValue({ low_stock_threshold: 50 } as never);
    inRouter(<Inventory />);
    const setting = screen.getByRole("region", { name: "Low stock alert" });
    expect(await within(setting).findByText("5")).toBeTruthy();
    // At 5, the 6-unit French lace is no longer low.
    const lace = (await screen.findByText("French lace, royal blue")).closest("li")!;
    expect(within(lace).getByText("In stock")).toBeTruthy();

    fireEvent.click(within(setting).getByRole("button", { name: "Change" }));
    fireEvent.change(within(setting).getByLabelText(/Mark stock as low/), { target: { value: "50" } });
    fireEvent.click(within(setting).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(vendorsApi.setStockAlert).toHaveBeenCalledWith(50));
    expect(await within(setting).findByText("50")).toBeTruthy();
    expect(within(screen.getByText("Ankara print").closest("li")!).getByText("Low")).toBeTruthy();
  });
});

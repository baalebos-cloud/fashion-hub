import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CheckoutPage } from "@/components/checkout/CheckoutPage";
import { checkoutApi } from "@/api/checkout.api";
import { paymentsApi } from "@/api/payments.api";
import type { Order } from "@/types/order";

const { summary } = vi.hoisted(() => ({ summary: { cart_id: "cart", revision: 4, currency: "NGN", subtotal: 70,
  items: [{ id: "line-a", product_variant_id: "variant-a", vendor_id: "vendor-a", vendor_name: "Store A", product_name: "Cotton", sku: "A", currency: "NGN", quantity: 2, unit_price_snapshot: 10, is_available: true },
    { id: "line-b", product_variant_id: "variant-b", vendor_id: "vendor-b", vendor_name: "Store B", product_name: "Silk", sku: "B", currency: "NGN", quantity: 1, unit_price_snapshot: 50, is_available: true }] } }));
vi.mock("@/hooks/use-cart", () => ({ useCart: () => ({ summary, isLoading: false, error: null }) }));
vi.mock("@/api/addresses.api", () => ({ addressesApi: { list: vi.fn().mockResolvedValue([{ id: "address", label: "Home", formatted_address: "10 Street", city: "Lagos" }]) } }));
vi.mock("@/api/checkout.api", () => ({ checkoutApi: { submit: vi.fn() } }));
vi.mock("@/api/payments.api", () => ({ paymentsApi: { initialize: vi.fn() } }));
function open() {
  render(<MemoryRouter><Routes><Route path="/" element={<CheckoutPage />} /><Route path="/app/professional/vendor-orders/:orderId" element={<h1>Order review</h1>} /></Routes></MemoryRouter>);
}
afterEach(cleanup);
beforeEach(() => vi.clearAllMocks());
describe("material checkout", () => {
  it("submits the selected vendor with cart revision and a stable key on a lost response", async () => {
    vi.mocked(checkoutApi.submit).mockRejectedValue(new Error("Connection lost"));
    open();
    await screen.findByRole("option", { name: "Home: 10 Street, Lagos" });
    fireEvent.change(screen.getByLabelText("Vendor"), { target: { value: "vendor-b" } });
    const button = screen.getByRole("button", { name: "Create order and review total" });
    fireEvent.click(button);
    await waitFor(() => expect(checkoutApi.submit).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);
    await waitFor(() => expect(checkoutApi.submit).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(checkoutApi.submit).mock.calls.map(([payload]) => payload);
    expect(first).toEqual({ cart_id: "cart", cart_revision: 4, vendor_id: "vendor-b", delivery_address_id: "address", idempotency_key: expect.any(String) });
    expect(first).toEqual(second);
    expect(paymentsApi.initialize).not.toHaveBeenCalled();
  });
  it("opens the committed order for price review without initializing payment", async () => {
    vi.mocked(checkoutApi.submit).mockResolvedValue({ id: "created-order" } as Order);
    open();
    await screen.findByRole("option", { name: "Home: 10 Street, Lagos" });
    fireEvent.click(screen.getByRole("button", { name: "Create order and review total" }));
    await screen.findByRole("heading", { name: "Order review" });
    expect(paymentsApi.initialize).not.toHaveBeenCalled();
  });
});

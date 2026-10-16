import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import CreateOrder from "@/pages/customer/CreateOrder";
import { ordersApi } from "@/api/orders.api";

vi.mock("@/hooks/use-measurements", () => ({ useMeasurements: () => ({ profiles: [{ id: "measurements", label: "Mine" }], refetch: vi.fn() }) }));
vi.mock("@/hooks/use-designs", () => ({ useDesigns: () => ({ designs: [{ id: "design", title: "Catalog dress", base_price: 100, currency: "NGN" }], isLoading: false }) }));
vi.mock("@/components/ui/toast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock("@/api/professionals.api", () => ({ professionalsApi: { getById: vi.fn().mockResolvedValue({ id: "profile-id", user_id: "seller-account" }) } }));
vi.mock("@/api/addresses.api", () => ({ addressesApi: { list: vi.fn().mockResolvedValue([{ id: "address", label: "Home", formatted_address: "10 Test Street", city: "Lagos" }]) } }));
vi.mock("@/api/orders.api", () => ({ ordersApi: { create: vi.fn() } }));
afterEach(cleanup);

describe("catalog order submission", () => {
  it("uses the seller account ID, sends no client price, and keeps a stable retry key", async () => {
    vi.mocked(ordersApi.create).mockRejectedValue(new Error("Connection lost"));
    render(<MemoryRouter initialEntries={["/order/profile-id"]}><Routes><Route path="/order/:professionalId" element={<CreateOrder />} /></Routes></MemoryRouter>);
    await screen.findByRole("option", { name: "Home: 10 Test Street, Lagos" });
    fireEvent.change(screen.getByLabelText("Published design"), { target: { value: "design" } });
    fireEvent.change(screen.getByLabelText("Measurement profile"), { target: { value: "measurements" } });
    fireEvent.change(screen.getByLabelText("Delivery address"), { target: { value: "address" } });
    const button = screen.getByRole("button", { name: "Continue to checkout" });
    fireEvent.click(button);
    await waitFor(() => expect(ordersApi.create).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(button);
    await waitFor(() => expect(ordersApi.create).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(ordersApi.create).mock.calls.map(([payload]) => payload);
    expect(first).toEqual({ professional_user_id: "seller-account", items: [{ reference_type: "design", reference_id: "design", quantity: 1 }], delivery_address_id: "address", measurement_profile_id: "measurements", idempotency_key: expect.any(String) });
    expect(first.idempotency_key).toBe(second.idempotency_key);
  });
});

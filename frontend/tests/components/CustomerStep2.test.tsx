import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import CreateOrder from "@/pages/customer/CreateOrder";
import { ProfessionalCard } from "@/components/professionals/ProfessionalCard";
import { CUSTOMER_ORDER_NEXT_STEP } from "@/constants/order-status";
import type { Professional } from "@/types/professional";

vi.mock("@/hooks/use-measurements", () => ({ useMeasurements: () => ({ profiles: [
  { id: "partial", label: "Old profile", fields: [{ field_name: "chest", value: 104, unit: "cm" }] },
  { id: "complete", label: "New profile", fields: [{ field_name: "chest", value: 104, unit: "cm" }, { field_name: "sleeve_length", value: 63, unit: "cm" }] },
], refetch: vi.fn() }) }));
vi.mock("@/hooks/use-designs", () => ({ useDesigns: () => ({ designs: [
  { id: "agbada", title: "Royal blue agbada", base_price: 45000, currency: "NGN", required_measurement_fields: ["chest", "sleeve_length"] },
], isLoading: false }) }));
vi.mock("@/components/ui/toast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock("@/api/professionals.api", () => ({ professionalsApi: { getById: vi.fn().mockResolvedValue({ id: "p", user_id: "seller", business_name: "Kemi Couture" }) } }));
vi.mock("@/api/addresses.api", () => ({ addressesApi: { list: vi.fn().mockResolvedValue([{ id: "home", label: "Home", formatted_address: "14 Admiralty Way", city: "Lekki" }]) } }));
vi.mock("@/api/orders.api", () => ({ ordersApi: { create: vi.fn() } }));
afterEach(cleanup);

const pro = (over: Partial<Professional>): Professional => ({
  id: "p1", user_id: "u1", professional_type: "tailor", business_name: "Kemi Couture", is_verified: true,
  average_rating: 4.8, review_count: 126, accepts_new_orders: true, ...over,
});

describe("professional card", () => {
  it("shows verified and taking-orders as separate signals with real review counts", () => {
    render(<MemoryRouter><ProfessionalCard professional={pro({})} detailsPath="/p/p1" /></MemoryRouter>);
    expect(screen.getByText("✓ Verified")).toBeTruthy();
    expect(screen.getByText("Taking orders")).toBeTruthy();
    expect(screen.getByText("126 reviews")).toBeTruthy();
  });

  it("is honest about pending verification, paused orders and no reviews", () => {
    render(<MemoryRouter><ProfessionalCard professional={pro({ is_verified: false, accepts_new_orders: false, review_count: 0 })} detailsPath="/p/p1" /></MemoryRouter>);
    expect(screen.getByText("Verification pending")).toBeTruthy();
    expect(screen.getByText("Not taking orders")).toBeTruthy();
    expect(screen.getByText("No reviews yet")).toBeTruthy();
  });
});

describe("customer order next steps", () => {
  it("names the next step for live statuses and nothing for finished ones", () => {
    expect(CUSTOMER_ORDER_NEXT_STEP.in_production).toBe("Being made");
    expect(CUSTOMER_ORDER_NEXT_STEP.delivered).toMatch(/confirm you received it/);
    expect(CUSTOMER_ORDER_NEXT_STEP.completed).toBeUndefined();
  });
});

describe("ordering form", () => {
  it("blocks a profile missing a measurement the design needs, keeping other choices", async () => {
    render(<MemoryRouter initialEntries={["/order/p"]}><Routes><Route path="/order/:professionalId" element={<CreateOrder />} /></Routes></MemoryRouter>);
    await screen.findByRole("option", { name: "Home: 14 Admiralty Way, Lekki" });
    fireEvent.change(screen.getByLabelText("Published design"), { target: { value: "agbada" } });
    fireEvent.change(screen.getByLabelText("Delivery address"), { target: { value: "home" } });
    fireEvent.change(screen.getByLabelText("Measurement profile"), { target: { value: "partial" } });

    expect(screen.getByRole("alert").textContent).toMatch(/Add sleeve length to continue/);
    const button = screen.getByRole("button", { name: "Continue to checkout" });
    expect(button).toHaveProperty("disabled", true);

    fireEvent.change(screen.getByLabelText("Measurement profile"), { target: { value: "complete" } });
    expect(screen.queryByText(/Add sleeve length to continue/)).toBeNull();
    expect(button).toHaveProperty("disabled", false);
    expect(screen.getByText("Royal blue agbada", { selector: "dd" })).toBeTruthy();
  });
});

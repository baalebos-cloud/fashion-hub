import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Dropoff from "@/pages/delivery/Dropoff";
import { deliveriesApi } from "@/api/deliveries.api";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/api/deliveries.api", () => ({
  deliveriesApi: { markDelivered: vi.fn(), getById: vi.fn() },
  newIdempotencyKey: (() => { let n = 0; return () => `key-${++n}`; })(),
}));
vi.mock("@/hooks/use-delivery", () => ({ useDelivery: () => ({ delivery: { id: "d1", order_id: "o1", status: "in_transit", package_count: 2 } }) }));
vi.mock("@/components/calls/OrderContacts", () => ({ OrderContacts: () => null }));
afterEach(cleanup);

const renderDropoff = () => render(
  <MemoryRouter initialEntries={["/d/d1/dropoff"]}><Routes><Route path="/d/:deliveryId/dropoff" element={<Dropoff />} /></Routes></MemoryRouter>);

function enter(code: string) {
  fireEvent.change(screen.getByLabelText("Customer handover code"), { target: { value: code } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm delivered" }));
}

describe("rider handover code", () => {
  it("starts empty, counts wrong codes down, then locks after the backend refuses", async () => {
    renderDropoff();
    const field = screen.getByLabelText("Customer handover code") as HTMLInputElement;
    expect(field.value).toBe("");
    expect(screen.getByRole("button", { name: "Confirm delivered" })).toHaveProperty("disabled", true);
    expect(screen.getByText("Hand over all 2 packages you collected.")).toBeTruthy();

    vi.mocked(deliveriesApi.markDelivered).mockRejectedValueOnce(new ApiError("Incorrect handover code.", "VALIDATION_ERROR", 422, null));
    enter("111111");
    expect(await screen.findByText("Incorrect handover code. At most 4 tries left.")).toBeTruthy();
    expect(field.value).toBe("");

    vi.mocked(deliveriesApi.markDelivered).mockRejectedValueOnce(new ApiError("Too many incorrect codes. Contact support.", "FORBIDDEN", 403, null));
    enter("222222");
    expect(await screen.findByText(/This handover is locked; report a problem/)).toBeTruthy();
    expect(field.disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Confirm delivered" })).toHaveProperty("disabled", true);
  });
});

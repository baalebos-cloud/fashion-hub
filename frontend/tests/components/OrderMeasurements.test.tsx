import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { OrderMeasurementsCard } from "@/components/orders/OrderMeasurementsCard";
import { ordersApi } from "@/api/orders.api";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/api/orders.api", () => ({ ordersApi: { measurements: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("order measurements card", () => {
  it("shows the values saved on the order", async () => {
    vi.mocked(ordersApi.measurements).mockResolvedValue({ order_id: "o1", label: "My measurements", garment_type: "agbada",
      fields: [{ field_name: "chest", value: "92.50", unit: "cm" }, { field_name: "sleeve_length", value: "61.00", unit: "cm" }] });
    render(<OrderMeasurementsCard orderId="o1" status="accepted" />);
    const card = screen.getByRole("region", { name: "Customer measurements" });
    expect(await within(card).findByText("92.5 cm")).toBeTruthy();
    expect(within(card).getByText("Sleeve length")).toBeTruthy();
    expect(within(card).getByText("My measurements")).toBeTruthy();
    expect(within(card).getByText(/for agbada/)).toBeTruthy();
  });

  it("explains when they're not shown yet or any more", async () => {
    vi.mocked(ordersApi.measurements).mockRejectedValue(new ApiError("no", "FORBIDDEN", 403, null));
    render(<OrderMeasurementsCard orderId="o1" status="pending" />);
    expect(await screen.findByText(/once the customer has paid/)).toBeTruthy();
    cleanup();
    render(<OrderMeasurementsCard orderId="o1" status="completed" />);
    expect(await screen.findByText(/no longer shown now this order is closed/)).toBeTruthy();
  });

  it("handles a missing copy and a load failure", async () => {
    vi.mocked(ordersApi.measurements).mockRejectedValueOnce(new ApiError("none", "NOT_FOUND", 404, null));
    render(<OrderMeasurementsCard orderId="o1" status="accepted" />);
    expect(await screen.findByText(/No measurements were saved/)).toBeTruthy();
    cleanup();
    vi.mocked(ordersApi.measurements).mockRejectedValueOnce(new ApiError("Network error", "NETWORK", null, null));
    render(<OrderMeasurementsCard orderId="o1" status="accepted" />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't be loaded/);
  });
});

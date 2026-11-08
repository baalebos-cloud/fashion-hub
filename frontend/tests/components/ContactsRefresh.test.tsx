import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { CustomerDeliveryTracking } from "@/components/delivery/CustomerDeliveryTracking";
import { callsApi } from "@/api/calls.api";
import { deliveriesApi } from "@/api/deliveries.api";

vi.mock("@/api/calls.api", () => ({ callsApi: { contacts: vi.fn(), start: vi.fn() } }));
vi.mock("@/api/deliveries.api", () => ({ deliveriesApi: { getByOrder: vi.fn(), getPosition: vi.fn() } }));
afterEach(cleanup);

describe("contacts follow rider assignment", () => {
  it("reloads contacts when the rider key changes, so a newly assigned rider can be called", async () => {
    vi.mocked(callsApi.contacts)
      .mockResolvedValueOnce([{ party: "seller", display_name: "Kemi Couture", available: true }] as never)
      .mockResolvedValueOnce([{ party: "seller", display_name: "Kemi Couture", available: true },
        { party: "rider", display_name: "Sola", available: true }] as never);
    const { rerender } = render(<OrderContacts orderId="o1" refreshKey="" />);
    await screen.findByText("Kemi Couture");
    expect(screen.queryByText("Sola")).toBeNull();
    rerender(<OrderContacts orderId="o1" refreshKey="d1:Sola" />);
    expect(await screen.findByText("Sola")).toBeTruthy();
    expect(callsApi.contacts).toHaveBeenCalledTimes(2);
  });

  it("tracking reports the assigned rider to the page", async () => {
    vi.mocked(deliveriesApi.getByOrder).mockResolvedValue({ id: "d1", status: "assigned", rider_name: "Sola" } as never);
    const onRiderChange = vi.fn();
    render(<CustomerDeliveryTracking orderId="o1" onRiderChange={onRiderChange} />);
    await waitFor(() => expect(onRiderChange).toHaveBeenCalledWith("d1:Sola"));
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { DispatchTripCard } from "@/components/delivery/DispatchTripCard";
import { callsApi } from "@/api/calls.api";

vi.mock("@/api/calls.api", () => ({ callsApi: { contacts: vi.fn(), start: vi.fn() } }));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("order contacts", () => {
  it("lists callable parties and starts a masked call without showing numbers", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([
      { party: "seller", display_name: "Kemi Couture", available: true, reason: null },
      { party: "rider", display_name: "Sola", available: false, reason: "This person hasn't added a phone number yet." },
    ]);
    vi.mocked(callsApi.start).mockResolvedValue({
      call_id: "c1", status: "ringing_caller", callee_display_name: "Kemi Couture", your_phone_ending: "01" });
    render(<OrderContacts orderId="order-1" />);

    expect(await screen.findByText("Kemi Couture")).toBeTruthy();
    expect(screen.getByText("This person hasn't added a phone number yet.")).toBeTruthy();
    const [callSeller, callRider] = screen.getAllByRole("button", { name: /Call/ }) as HTMLButtonElement[];
    expect(callRider.disabled).toBe(true);

    fireEvent.click(callSeller);
    expect(await screen.findByText(
      "Tailora is calling your phone ending 01. Answer to be connected to Kemi Couture. Your number stays private.")).toBeTruthy();
    expect(callsApi.start).toHaveBeenCalledWith("order-1", "seller");
    expect(document.body.textContent).not.toMatch(/\+?234\d{6,}|0\d{10}/);
  });

  it("explains why a call could not start", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([
      { party: "buyer", display_name: "Ada", available: true, reason: null }]);
    vi.mocked(callsApi.start).mockRejectedValue(new Error("Add your phone number in Settings so Tailora can connect your call."));
    render(<OrderContacts orderId="order-1" />);
    fireEvent.click(await screen.findByRole("button", { name: /Call/ }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/Settings/);
  });

  it("renders nothing for orders with nobody to call", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([]);
    const { container } = render(<OrderContacts orderId="order-1" />);
    await vi.waitFor(() => expect(callsApi.contacts).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

describe("rider trip card", () => {
  it("offers masked calls instead of tel: or WhatsApp links", () => {
    render(<DispatchTripCard trip={{
      id: "d1", order_id: "order-9", status: "in_transit", delivery_fee: 0, straight_line_km: 3.2,
      pickup: { address: "Shop", latitude: 6.5, longitude: 3.3, contact_name: "Kemi", can_call: true },
      dropoff: { address: "Home", latitude: 6.6, longitude: 3.4, contact_name: "Ada", can_call: false },
    }} />);
    expect(screen.getByRole("button", { name: /Call pickup contact/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Call customer/ })).toBeNull();
    expect(document.querySelector('a[href^="tel:"], a[href*="wa.me"]')).toBeNull();
  });
});

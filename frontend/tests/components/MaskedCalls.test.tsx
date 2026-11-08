import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { OrderContacts } from "@/components/calls/OrderContacts";
import { DispatchTripCard } from "@/components/delivery/DispatchTripCard";
import { callsApi } from "@/api/calls.api";
import { CallCenter } from "@/components/calls/CallCenter";
import { useCallStore } from "@/store/call.store";
import { useAuthStore } from "@/store/auth.store";
import { AppCalls } from "@/components/calls/AppCalls";
import { joinVoiceRoom, MicrophoneBlockedError } from "@/lib/calls/voice-room";

vi.mock("@/api/calls.api", () => ({ callsApi: { contacts: vi.fn(), start: vi.fn(), startApp: vi.fn(), status: vi.fn(),
  incoming: vi.fn().mockResolvedValue([]), answer: vi.fn(), heartbeat: vi.fn(), decline: vi.fn().mockResolvedValue({}), cancel: vi.fn().mockResolvedValue({}),
  end: vi.fn().mockResolvedValue({}) } }));
const room = vi.hoisted(() => ({ setMuted: vi.fn().mockResolvedValue(undefined), leave: vi.fn().mockResolvedValue(undefined) }));
vi.mock("@/lib/calls/voice-room", () => ({
  MicrophoneBlockedError: class MicrophoneBlockedError extends Error {},
  joinVoiceRoom: vi.fn(async () => room),
}));
const CALL = { call_id: "c1", status: "ringing" as const, order_id: "order-1", order_number: "TL-1", other_party_name: "Kemi Couture",
  you_are: "caller" as const, started_at: null, answered_at: null };
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => { vi.clearAllMocks(); vi.mocked(callsApi.incoming).mockResolvedValue([]); });
afterEach(() => { cleanup(); useCallStore.getState().dismiss(); });

describe("order contacts", () => {
  it("lists callable parties and starts an in-app call without showing numbers", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([
      { party: "seller", display_name: "Kemi Couture", available: true, reason: null },
      { party: "rider", display_name: "Sola", available: false, reason: "Calls close when an order is finished." },
    ]);
    vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
    render(<><OrderContacts orderId="order-1" /><CallCenter enabled={false} /></>);

    expect(await screen.findByText("Kemi Couture")).toBeTruthy();
    const [callSeller, callRider] = screen.getAllByRole("button", { name: /Call/ }) as HTMLButtonElement[];
    expect(callRider.disabled).toBe(true);

    fireEvent.click(callSeller);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Ringing…")).toBeTruthy();
    expect(callsApi.startApp).toHaveBeenCalledWith("order-1", "seller");
    expect(joinVoiceRoom).toHaveBeenCalledWith("wss://x", "t", expect.any(Object));
    expect(document.body.textContent).not.toMatch(/\+?234\d{6,}|0\d{10}/);
  });

  it("explains why a call could not start", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([
      { party: "buyer", display_name: "Ada", available: true, reason: null }]);
    vi.mocked(callsApi.startApp).mockRejectedValue(new Error("Ada is on another call. Try again shortly."));
    render(<><OrderContacts orderId="order-1" /><CallCenter enabled={false} /></>);
    fireEvent.click(await screen.findByRole("button", { name: /Call/ }));
    expect(await screen.findByText("Ada is on another call. Try again shortly.")).toBeTruthy();
  });

  it("renders nothing for orders with nobody to call", async () => {
    vi.mocked(callsApi.contacts).mockResolvedValue([]);
    const { container } = render(<OrderContacts orderId="order-1" />);
    await vi.waitFor(() => expect(callsApi.contacts).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

describe("in-app call screen", () => {
  it("shows the call once they answer, mutes, and hangs up", async () => {
    vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
    vi.mocked(callsApi.status).mockResolvedValue({ ...CALL, status: "active" });
    render(<CallCenter enabled={false} />);
    await act(async () => { await useCallStore.getState().start("order-1", "seller", "Kemi Couture"); });
    await act(async () => { await useCallStore.getState().sync({ ...CALL, status: "active" }); });
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("0:00")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: /Mute/ }));
    await waitFor(() => expect(room.setMuted).toHaveBeenCalledWith(true));
    fireEvent.click(within(dialog).getByRole("button", { name: "Hang up" }));
    await waitFor(() => expect(callsApi.end).toHaveBeenCalledWith("c1"));
    expect(room.leave).toHaveBeenCalled();
    expect(await screen.findByText("Call ended.")).toBeTruthy();
  });

  it("ends with a clear message when they decline", async () => {
    vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
    render(<CallCenter enabled={false} />);
    await act(async () => { await useCallStore.getState().start("order-1", "seller", "Kemi Couture"); });
    await act(async () => { await useCallStore.getState().sync({ ...CALL, status: "declined" }); });
    expect(screen.getByText(/They're busy right now/)).toBeTruthy();
    expect(room.leave).toHaveBeenCalled();
  });

  it("rings for an incoming call and connects on answer", async () => {
    vi.mocked(callsApi.incoming).mockResolvedValue([{ ...CALL, you_are: "callee", other_party_name: "Ada" }]);
    vi.mocked(callsApi.answer).mockResolvedValue({ ...CALL, status: "active", you_are: "callee", other_party_name: "Ada", token: "t2", url: "wss://x" });
    render(<CallCenter />);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Incoming call")).toBeTruthy();
    expect(within(dialog).getByText("Ada")).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Answer" }));
    await waitFor(() => expect(callsApi.answer).toHaveBeenCalledWith("c1"));
    expect(joinVoiceRoom).toHaveBeenCalledWith("wss://x", "t2", expect.any(Object));
    expect(await within(dialog).findByRole("button", { name: "Hang up" })).toBeTruthy();
  });

  it("declines an incoming call", async () => {
    vi.mocked(callsApi.incoming).mockResolvedValueOnce([{ ...CALL, you_are: "callee", other_party_name: "Ada" }]).mockResolvedValue([]);
    render(<CallCenter />);
    fireEvent.click(await screen.findByRole("button", { name: "Decline" }));
    await waitFor(() => expect(callsApi.decline).toHaveBeenCalledWith("c1"));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("explains a blocked microphone", async () => {
    vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
    vi.mocked(joinVoiceRoom).mockRejectedValueOnce(new MicrophoneBlockedError("Allow microphone access to make calls."));
    render(<CallCenter enabled={false} />);
    await act(async () => { await useCallStore.getState().start("order-1", "seller", "Kemi Couture"); });
    expect(screen.getByText("Allow microphone access to make calls.")).toBeTruthy();
    expect(callsApi.cancel).toHaveBeenCalledWith("c1");
  });
});

describe("rider trip card", () => {
  it("offers in-app calls instead of tel: or WhatsApp links", () => {
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

describe("calls that end on their own", () => {
  it("stops ringing when the caller gives up", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.mocked(callsApi.status).mockResolvedValue({ ...CALL, status: "cancelled", you_are: "callee", other_party_name: "Ada" });
      render(<CallCenter enabled={false} />);
      act(() => { useCallStore.getState().ring({ ...CALL, you_are: "callee", other_party_name: "Ada" }); });
      expect(screen.getByText("Incoming call")).toBeTruthy();
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
      expect(screen.getByText("Missed call from Ada.")).toBeTruthy();
      expect(screen.queryByRole("button", { name: "Answer" })).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it("sends heartbeats during a call and ends if the server says it's over", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
      vi.mocked(callsApi.heartbeat).mockResolvedValueOnce({ ...CALL, status: "active" }).mockResolvedValue({ ...CALL, status: "ended" });
      render(<CallCenter enabled={false} />);
      await act(async () => { await useCallStore.getState().start("order-1", "seller", "Kemi Couture"); });
      await act(async () => { await useCallStore.getState().sync({ ...CALL, status: "active" }); });
      await act(async () => { await vi.advanceTimersByTimeAsync(15100); });
      expect(callsApi.heartbeat).toHaveBeenCalledWith("c1");
      expect(useCallStore.getState().phase).toBe("connected");
      await act(async () => { await vi.advanceTimersByTimeAsync(15100); });
      expect(useCallStore.getState().phase).toBe("ended");
      expect(room.leave).toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });

  it("hangs up and releases the microphone when the session ends", async () => {
    vi.mocked(callsApi.startApp).mockResolvedValue({ ...CALL, token: "t", url: "wss://x" });
    useAuthStore.setState({ user: { id: "c1", role: "customer" } as never, isAuthenticated: true });
    render(<AppCalls />);
    await act(async () => { await useCallStore.getState().start("order-1", "seller", "Kemi Couture"); });
    await act(async () => { await useCallStore.getState().sync({ ...CALL, status: "active" }); });
    await act(async () => { useAuthStore.setState({ user: null, isAuthenticated: false }); });
    await waitFor(() => expect(callsApi.end).toHaveBeenCalledWith("c1"));
    expect(room.leave).toHaveBeenCalled();
    expect(useCallStore.getState().phase).toBe("idle");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});


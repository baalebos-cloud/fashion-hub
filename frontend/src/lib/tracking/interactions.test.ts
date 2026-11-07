import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { interactionsApi } from "@/api/interactions.api";
import {
  OPT_OUT_KEY, discardPendingInteractions, flush, getAnonymousId, resetTrackingForTests,
  setBrowserOptOut, trackBookingStarted, trackSearch, trackView,
} from "@/lib/tracking/interactions";

vi.mock("@/api/interactions.api", () => ({
  interactionsApi: { send: vi.fn().mockResolvedValue(1), getPreference: vi.fn(), setPreference: vi.fn() },
}));
const send = vi.mocked(interactionsApi.send);

beforeEach(() => {
  vi.useFakeTimers();
  localStorage.clear();
  resetTrackingForTests();
  send.mockClear();
  Object.defineProperty(navigator, "globalPrivacyControl", { value: undefined, configurable: true });
});
afterEach(() => vi.useRealTimers());

describe("shopping activity tracker", () => {
  it("batches events and sends them with a stable browser ID", async () => {
    trackView("product", "p1", "product_page");
    trackBookingStarted("t1");
    expect(send).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(3000);
    expect(send).toHaveBeenCalledTimes(1);
    const batch = send.mock.calls[0][0];
    expect(batch.anonymous_id).toBe(getAnonymousId());
    expect(batch.events).toEqual([
      { event_type: "view", item_type: "product", item_id: "p1", source: "product_page" },
      { event_type: "booking_started", item_type: "professional", item_id: "t1", source: "booking" },
    ]);
  });

  it("records a search once the person stops typing, ignoring one-letter queries", async () => {
    for (const text of ["a", "ag", "agb", "agbada"]) trackSearch(text, "tailor_search");
    await vi.advanceTimersByTimeAsync(1500 + 3000);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0].events).toEqual([
      { event_type: "search", search_query: "agbada", source: "tailor_search" },
    ]);
  });

  it("sends nothing when the browser asks sites not to track", async () => {
    Object.defineProperty(navigator, "globalPrivacyControl", { value: true, configurable: true });
    trackView("design", "d1", "booking");
    await vi.advanceTimersByTimeAsync(5000);
    expect(send).not.toHaveBeenCalled();
  });

  it("stops on this browser and forgets its ID when the visitor opts out", async () => {
    const before = getAnonymousId();
    setBrowserOptOut(true);
    expect(localStorage.getItem(OPT_OUT_KEY)).toBe("1");
    trackView("design", "d1", "booking");
    await flush();
    expect(send).not.toHaveBeenCalled();
    setBrowserOptOut(false);
    expect(getAnonymousId()).not.toBe(before);
  });

  it("drops queued events and starts a new browser ID on sign-out", async () => {
    const before = getAnonymousId();
    trackView("product", "p1", "product_page");
    discardPendingInteractions({ newBrowserId: true });
    await flush();
    expect(send).not.toHaveBeenCalled();
    expect(getAnonymousId()).not.toBe(before);
  });

  it("never throws when sending fails", async () => {
    send.mockRejectedValueOnce(new Error("offline"));
    trackView("product", "p1", "product_page");
    await expect(flush()).resolves.toBeUndefined();
  });
});

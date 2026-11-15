import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { RiderGpsSharing } from "@/components/delivery/RiderGpsSharing";
import { RiderSharingProvider } from "@/components/delivery/RiderSharingProvider";
import { deliveriesApi } from "@/api/deliveries.api";
import { ApiError } from "@/lib/api/errors";
import { describeFreshness } from "@/lib/utils/tracking";

vi.mock("@/api/deliveries.api", () => ({
  deliveriesApi: { startPosition: vi.fn(), publishPosition: vi.fn(), stopPosition: vi.fn(), reportPositionState: vi.fn() },
}));

let onFix: PositionCallback = () => undefined;
let onFail: PositionErrorCallback = () => undefined;

function fix(speed: number | null = 5, ageMs = 0): GeolocationPosition {
  return { timestamp: Date.now() - ageMs, coords: { latitude: 6.48, longitude: 3.42, accuracy: 12, speed,
    altitude: null, altitudeAccuracy: null, heading: null, toJSON: () => ({}) }, toJSON: () => ({}) } as GeolocationPosition;
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.clearAllMocks();
  Object.defineProperty(navigator, "geolocation", { configurable: true, value: {
    watchPosition: (ok: PositionCallback, bad: PositionErrorCallback) => { onFix = ok; onFail = bad; return 7; },
    clearWatch: vi.fn(),
  } });
  vi.mocked(deliveriesApi.startPosition).mockResolvedValue("t".repeat(43));
  vi.mocked(deliveriesApi.stopPosition).mockResolvedValue();
  vi.mocked(deliveriesApi.reportPositionState).mockResolvedValue();
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

async function startSharing() {
  render(<RiderSharingProvider><RiderGpsSharing deliveryId="d1" /></RiderSharingProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Start sharing my location" }));
  await screen.findByRole("button", { name: "Stop sharing" });
}

describe("rider location sharing", () => {
  it("sends the phone's fix time and keeps the latest point through a dropped connection", async () => {
    vi.mocked(deliveriesApi.publishPosition)
      .mockRejectedValueOnce(new ApiError("Network error", "NETWORK", null, null))
      .mockResolvedValue({ latitude: 6.48, longitude: 3.42, accuracy_m: 12, recorded_at: "", accepted: true });
    await startSharing();
    await act(async () => { onFix(fix(5)); });
    expect(await screen.findByText("Reconnecting…")).toBeTruthy();
    const sent = vi.mocked(deliveriesApi.publishPosition).mock.calls[0][1];
    expect(sent.recorded_at).toMatch(/T/);
    expect(sent.speed_mps).toBe(5);
    await act(async () => { await vi.advanceTimersByTimeAsync(5_000); });
    expect(deliveriesApi.publishPosition).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Sharing live")).toBeTruthy();
  });

  it("restarts an expired sharing session once and resends", async () => {
    vi.mocked(deliveriesApi.publishPosition)
      .mockRejectedValueOnce(new ApiError("GPS sharing is not active.", "FORBIDDEN", 403, null))
      .mockResolvedValue({ latitude: 6.48, longitude: 3.42, accuracy_m: 12, recorded_at: "", accepted: true });
    await startSharing();
    await act(async () => { onFix(fix(5)); });
    await act(async () => { await vi.advanceTimersByTimeAsync(10); });
    expect(deliveriesApi.startPosition).toHaveBeenCalledTimes(2);
    expect(deliveriesApi.publishPosition).toHaveBeenCalledTimes(2);
  });

  it("tells the customer when location permission is off", async () => {
    await startSharing();
    await act(async () => { onFail({ code: 1, message: "denied", PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 } as GeolocationPositionError); });
    expect(await screen.findByText("Location permission off")).toBeTruthy();
    expect(deliveriesApi.reportPositionState).toHaveBeenCalledWith("d1", "t".repeat(43), "permission_denied");
  });
});

describe("sharing across screens", () => {
  function Screens() {
    const [page, setPage] = useState<"job" | "dropoff">("job");
    return (
      <RiderSharingProvider>
        <button type="button" onClick={() => setPage(page === "job" ? "dropoff" : "job")}>switch screen</button>
        {page === "job" ? <RiderGpsSharing deliveryId="d1" /> : <p>Confirm drop-off</p>}
      </RiderSharingProvider>
    );
  }

  it("keeps sharing when the rider moves to another screen and back", async () => {
    vi.mocked(deliveriesApi.publishPosition).mockResolvedValue({ latitude: 6.48, longitude: 3.42, accuracy_m: 12, recorded_at: "", accepted: true });
    render(<Screens />);
    fireEvent.click(screen.getByRole("button", { name: "Start sharing my location" }));
    await screen.findByRole("button", { name: "Stop sharing" });
    fireEvent.click(screen.getByRole("button", { name: "switch screen" }));
    expect(screen.getByText("Confirm drop-off")).toBeTruthy();
    await act(async () => { onFix(fix(5)); });
    expect(deliveriesApi.publishPosition).toHaveBeenCalledTimes(1); // still sending from the other screen
    expect(deliveriesApi.stopPosition).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "switch screen" }));
    expect(await screen.findByText("Sharing live")).toBeTruthy();
  });

  it("stops sharing when the rider leaves the rider area", async () => {
    const view = render(<Screens />);
    fireEvent.click(screen.getByRole("button", { name: "Start sharing my location" }));
    await screen.findByRole("button", { name: "Stop sharing" });
    view.unmount();
    expect(deliveriesApi.stopPosition).toHaveBeenCalledWith("d1");
  });
});

describe("freshness words", () => {
  it("never presents an old point as current", () => {
    expect(describeFreshness("live", 8)).toEqual({ label: "Live · updated 8s ago", current: true });
    expect(describeFreshness("delayed", 70).current).toBe(true);
    expect(describeFreshness("last_known", 300)).toEqual({ label: "Last seen 5 min ago. This isn't the rider's current position", current: false });
    expect(describeFreshness("permission_denied").label).toBe("The rider's location is switched off");
  });
});

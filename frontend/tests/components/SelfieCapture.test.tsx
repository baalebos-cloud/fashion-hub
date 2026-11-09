import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SelfieCapture } from "@/components/verification/SelfieCapture";
import { uploadFile } from "@/lib/storage/file-storage";

vi.mock("@/lib/storage/file-storage", () => ({ uploadFile: vi.fn(async () => ({ url: "kyc/u1/selfie.jpg" })) }));

const stop = vi.fn();
beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:selfie");
  URL.revokeObjectURL = vi.fn();
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => { cb(0); return 0; });
  Object.defineProperty(HTMLMediaElement.prototype, "play", { configurable: true, value: vi.fn(async () => {}) });
  Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", { configurable: true, get: () => 1280 });
  Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", { configurable: true, get: () => 960 });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage: vi.fn() } as unknown as CanvasRenderingContext2D);
  vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function (cb) { cb(new Blob(["jpeg"], { type: "image/jpeg" })); });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function camera(getUserMedia: () => Promise<unknown>) {
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: vi.fn(getUserMedia) } });
}

describe("live selfie", () => {
  it("opens the front camera in the page, captures, and uploads privately", async () => {
    camera(async () => ({ getTracks: () => [{ stop }] }));
    const onUploaded = vi.fn();
    render(<SelfieCapture onUploaded={onUploaded} />);
    fireEvent.click(screen.getByRole("button", { name: "Take selfie" }));
    expect(await screen.findByLabelText("Camera preview")).toBeTruthy();
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(expect.objectContaining({
      video: expect.objectContaining({ facingMode: "user" }), audio: false }));
    fireEvent.click(screen.getByRole("button", { name: "Capture" }));
    await waitFor(() => expect(onUploaded).toHaveBeenLastCalledWith("kyc/u1/selfie.jpg"));
    expect(vi.mocked(uploadFile).mock.calls[0][0]).toBe("/media/upload?purpose=kyc");
    expect(stop).toHaveBeenCalled(); // camera turned off after capture
    expect(screen.getByAltText("Your selfie")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retake selfie" })).toBeTruthy();
    // No way to pick a gallery photo instead.
    expect(document.querySelector('input[type="file"]')).toBeNull();
  });

  it("explains a blocked camera", async () => {
    camera(async () => { throw new DOMException("denied", "NotAllowedError"); });
    render(<SelfieCapture onUploaded={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Take selfie" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/Camera access is blocked/);
  });

  it("explains a device with no camera", async () => {
    camera(async () => { throw new DOMException("none", "NotFoundError"); });
    render(<SelfieCapture onUploaded={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Take selfie" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/No camera was found/);
  });

  it("turns the camera off if the person left while the permission prompt was open", async () => {
    let grant: (stream: unknown) => void = () => {};
    camera(() => new Promise((resolve) => { grant = resolve; }));
    const { unmount } = render(<SelfieCapture onUploaded={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Take selfie" }));
    unmount();
    grant({ getTracks: () => [{ stop }] });
    await waitFor(() => expect(stop).toHaveBeenCalled());
  });
});

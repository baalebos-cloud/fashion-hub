import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MeasurementScanner } from "@/components/measurements/MeasurementScanner";
import { aiService } from "@/services/aiService";

vi.mock("@/services/aiService", () => ({ aiService: { analyzeMeasurementPhotos: vi.fn() } }));
// Photos are resized to JPEG on the phone before analysis; stand in for that step.
const prepared = vi.hoisted(() => new Map<File, File>());
vi.mock("@/lib/media/prepare-image", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/media/prepare-image")>()),
  prepareImage: vi.fn(async (file: File) => {
    if (file.name === "broken.heic") throw new Error("This photo couldn't be opened. Choose a JPEG or PNG photo.");
    const ready = new File(["jpeg"], file.name.replace(/\.[^.]+$/, ".jpg"), { type: "image/jpeg" });
    prepared.set(file, ready);
    return ready;
  }),
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const photo = (name = "me.jpg", type = "image/jpeg", size = 2000) => new File([new Uint8Array(size)], name, { type });

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});
afterEach(cleanup);

describe("Measure with photos", () => {
  it("drafts the form from photos, lets the customer edit, and applies only after confirmation", async () => {
    vi.mocked(aiService.analyzeMeasurementPhotos).mockResolvedValue({
      fields: [
        { field_name: "chest", value: 98.5, unit: "cm", source: "estimate", confidence: 0.55 },
        { field_name: "waist", value: 82, unit: "cm", source: "tape", confidence: 0.92 },
      ],
      notes: "Fitted clothing gives better results.", photo_issues: ["feet cut off"],
      provider: "vertex_ai", requires_review: true,
    });
    const onApply = vi.fn();
    render(<MeasurementScanner onApply={onApply} garmentType="kaftan" />);

    const body = photo();
    const tape = photo("tape.png", "image/png");
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [body] } });
    expect(await screen.findByAltText("Full-body photo")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Measurement photos"), { target: { files: [tape] } });
    expect(await screen.findByAltText("Measurement photo 1")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Your height (cm)"), { target: { value: "172" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyse photos" }));

    expect(await screen.findByText("Estimate · 55%")).toBeTruthy();
    expect(screen.getByText("Read from your photo · 92%")).toBeTruthy();
    expect(screen.getByText("feet cut off")).toBeTruthy();
    expect(aiService.analyzeMeasurementPhotos).toHaveBeenCalledWith({
      bodyPhoto: prepared.get(body), tapePhotos: [prepared.get(tape)], heightCm: 172, garmentType: "kaftan",
    });

    const apply = screen.getByRole("button", { name: "Use these in my form" });
    expect((apply as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Chest in centimetres"), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(apply);

    expect(onApply).toHaveBeenCalledWith({
      chest: { value: 100, source: "estimate" },
      waist: { value: 82, source: "tape" },
    });
  });

  it("needs a photo before analysing, accepts iPhone photos, and explains unusable ones", async () => {
    render(<MeasurementScanner onApply={vi.fn()} />);
    expect((screen.getByRole("button", { name: "Analyse photos" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo("notes.txt", "text/plain")] } });
    expect((await screen.findByRole("alert")).textContent).toMatch(/Please choose a photo/);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo("broken.heic", "image/heic")] } });
    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't be opened/);
    // A big iPhone photo is fine: it is resized before sending.
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo("IMG_0001.HEIC", "image/heic", 9_000_000)] } });
    expect(await screen.findByAltText("Full-body photo")).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("blocks an out-of-range height and explains why", async () => {
    render(<MeasurementScanner onApply={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo()] } });
    await screen.findByAltText("Full-body photo");
    fireEvent.change(screen.getByLabelText("Your height (cm)"), { target: { value: "30" } });
    expect(screen.getByText("Enter a height between 100 and 230 cm.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Analyse photos" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("falls back to manual entry when analysis is unavailable", async () => {
    vi.mocked(aiService.analyzeMeasurementPhotos).mockRejectedValue(
      new Error("Photo analysis is unavailable right now. Enter measurements manually."));
    render(<MeasurementScanner onApply={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Measurement photos"), { target: { files: [photo("t.jpg")] } });
    await screen.findByAltText("Measurement photo 1");
    fireEvent.click(screen.getByRole("button", { name: "Analyse photos" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/Enter measurements manually/));
  });
});

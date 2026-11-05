import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MeasurementScanner } from "@/components/measurements/MeasurementScanner";
import { aiService } from "@/services/aiService";

vi.mock("@/services/aiService", () => ({ aiService: { analyzeMeasurementPhotos: vi.fn() } }));
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
    fireEvent.change(screen.getByLabelText("Tape-measure photos"), { target: { files: [tape] } });
    fireEvent.change(screen.getByLabelText("Your height (cm)"), { target: { value: "172" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyse photos" }));

    expect(await screen.findByText("Estimate · 55%")).toBeTruthy();
    expect(screen.getByText("Read from tape · 92%")).toBeTruthy();
    expect(screen.getByText("feet cut off")).toBeTruthy();
    expect(aiService.analyzeMeasurementPhotos).toHaveBeenCalledWith({
      bodyPhoto: body, tapePhotos: [tape], heightCm: 172, garmentType: "kaftan",
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

  it("needs a photo before analysing and rejects unsupported files", () => {
    render(<MeasurementScanner onApply={vi.fn()} />);
    expect((screen.getByRole("button", { name: "Analyse photos" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo("x.gif", "image/gif")] } });
    expect(screen.getByRole("alert").textContent).toMatch(/JPEG, PNG or WebP/);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo("big.jpg", "image/jpeg", 5_000_001)] } });
    expect(screen.getByRole("alert").textContent).toMatch(/under 5 MB/);
  });

  it("blocks an out-of-range height and explains why", () => {
    render(<MeasurementScanner onApply={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Full-body photo"), { target: { files: [photo()] } });
    fireEvent.change(screen.getByLabelText("Your height (cm)"), { target: { value: "30" } });
    expect(screen.getByText("Enter a height between 100 and 230 cm.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Analyse photos" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("falls back to manual entry when analysis is unavailable", async () => {
    vi.mocked(aiService.analyzeMeasurementPhotos).mockRejectedValue(
      new Error("Photo analysis is unavailable right now. Enter measurements manually."));
    render(<MeasurementScanner onApply={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Tape-measure photos"), { target: { files: [photo("t.jpg")] } });
    fireEvent.click(screen.getByRole("button", { name: "Analyse photos" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/Enter measurements manually/));
  });
});

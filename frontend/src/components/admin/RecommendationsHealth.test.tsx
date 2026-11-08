import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { RecommendationsHealth } from "@/components/admin/RecommendationsHealth";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn() } }));
afterEach(cleanup);

const side = (shown: number, click: number | null, conv: number | null) =>
  ({ shown, clicked: 0, converted: 0, click_rate: click, conversion_rate: conv });

describe("recommendations health card", () => {
  it("shows each surface's rules vs learned numbers and the verdict", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: {
      mode: "experiment", experiment: "ranking_v1", report_days: 30,
      data: { events_last_30_days: 1200, shoppers_last_30_days: 80, related_pairs: 340, related_items_built_at: null },
      surfaces: [{ surface: "picked_for_you", rules: side(210, 0.05, 0.01), learned: side(205, 0.12, 0.02),
        verdict: { status: "learned_better", message: "Learned ranking gets more clicks (12.0% vs 5.0%)." } }],
    } });
    render(<RecommendationsHealth />);
    expect(await screen.findByText(/Test running/)).toBeTruthy();
    expect(screen.getByText("Picked for you")).toBeTruthy();
    expect(screen.getByText("12.0%")).toBeTruthy();
    expect(screen.getByText("5.0%")).toBeTruthy();
    expect(screen.getByText(/Learned ranking gets more clicks/)).toBeTruthy();
    expect(screen.getByText(/not built yet/)).toBeTruthy();
  });

  it("reports a load failure", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("403"));
    render(<RecommendationsHealth />);
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { DeliveryInsights } from "@/components/admin/DeliveryInsights";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn() } }));
afterEach(cleanup);

describe("delivery insights", () => {
  it("shows the summary, evidence-backed suggestions and the ETA backtest", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: {
      readiness: { completed_deliveries: 25, days_of_history: 20, ready_for_models: false, message: "Baselines only for now: 25 of 500 completed deliveries." },
      eta_calibration: { enabled: false, by_vehicle: { bike: { samples: 25, factor: 1.52, usable: true, reason: null,
        backtest: { tested_on: 13, mean_error_minutes_raw: 16.0, mean_error_minutes_calibrated: 1.1 } } } },
      riders: [{ partner_id: "p1", first_name: "Sola", deliveries: 25, median_minutes_to_pickup: 10, median_trip_minutes: 46, on_time_share: 0.92, offer_acceptance: null }],
      demand: { busiest_hours: [{ day: "Fri", hour: 17, average_jobs: 3.5 }], sample_requests: 40, timezone: "WAT (UTC+1)" },
      routes: { multistop_routes: 0, planned_minutes_saved_total: 0, median_actual_vs_estimated_trip: 1.52, trips_measured: 25 },
      recommendations: [{ code: "eta_calibration", recommendation: "Consider switching on ETA calibration (bike trips take 1.52x the estimate).",
        evidence: { tested_on: 13 }, confidence: "medium", reasoning: "Smaller average error on recent deliveries.", version: "delivery-insights-v1" }],
      summary: { summary: "25 deliveries completed so far.", source: "rules", version: "delivery-insights-v1" },
    } });
    render(<DeliveryInsights />);
    expect(await screen.findByText("25 deliveries completed so far.")).toBeTruthy();
    expect(screen.getByText(/Baselines only for now/)).toBeTruthy();
    expect(screen.getByText(/Consider switching on ETA calibration/)).toBeTruthy();
    expect(screen.getByText(/16 min raw vs 1.1 min calibrated/)).toBeTruthy();
    expect(screen.getByText("Fri 17:00 · about 3.5 jobs")).toBeTruthy();
    expect(screen.getByText("92%")).toBeTruthy();
  });
});

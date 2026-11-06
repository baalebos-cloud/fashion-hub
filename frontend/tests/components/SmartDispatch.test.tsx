import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SuggestedRiders } from "@/components/dispatch/SuggestedRiders";
import { adminDispatchApi } from "@/api/admin-dispatch.api";

vi.mock("@/api/admin-dispatch.api", () => ({ adminDispatchApi: { candidates: vi.fn(), assignWaiting: vi.fn() } }));
vi.mock("@/lib/utils/errors", () => ({ getDisplayErrorMessage: (_e: unknown, f: string) => f }));
afterEach(cleanup);

describe("suggested riders", () => {
  it("shows ranked riders with reasons and assigns with an audit reason", async () => {
    vi.mocked(adminDispatchApi.candidates).mockResolvedValue([
      { partner_id: "p1", first_name: "Sola", vehicle_type: "bike", rating: 4.6, score: 82.5, pickup_eta_minutes: 6,
        eta_source: "google_routes", explanation: "pickup in about 6 min (road route); accepts 90% of offers", version: "dispatch-score-v1" },
    ]);
    vi.mocked(adminDispatchApi.assignWaiting).mockResolvedValue();
    const onAssigned = vi.fn();
    render(<SuggestedRiders requestId="r1" onAssigned={onAssigned} />);
    fireEvent.click(screen.getByRole("button", { name: "Suggested riders" }));
    expect(await screen.findByText(/pickup in about 6 min/)).toBeTruthy();
    expect(screen.getByLabelText("Score 82.5 out of 100")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Assign" }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Closest reliable rider" } });
    fireEvent.click(screen.getByRole("button", { name: "Assign to Sola" }));
    await waitFor(() => expect(adminDispatchApi.assignWaiting).toHaveBeenCalledWith("r1", "p1", "Closest reliable rider"));
    expect(onAssigned).toHaveBeenCalled();
  });
});

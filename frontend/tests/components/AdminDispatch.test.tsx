import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import Deliveries from "@/pages/admin/Deliveries";
import { adminDispatchApi } from "@/api/admin-dispatch.api";

vi.mock("@/api/admin-dispatch.api", () => ({
  adminDispatchApi: { board: vi.fn(), issues: vi.fn(), riders: vi.fn(), release: vi.fn(), reassign: vi.fn(),
    cancelRequest: vi.fn(), updateIssue: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const now = new Date().toISOString();
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(adminDispatchApi.board).mockResolvedValue({
    unassigned_count: 1, active_count: 2, available_verified_riders: 1, open_issue_count: 1,
    pending: [{ id: "r1", order_id: "o1", order_number: "VO-11", order_type: "vendor_order", status: "requested", created_at: now }],
    active: [
      { id: "d1", order_id: "o2", order_number: "CO-22", order_type: "customer_order", status: "assigned",
        delivery_partner_id: "p1", rider_first_name: "Sola", vehicle_type: "bike", open_issue_count: 1, created_at: now },
      { id: "d2", order_id: "o3", order_number: "CO-33", order_type: "customer_order", status: "in_transit",
        delivery_partner_id: "p3", rider_first_name: "Ade", vehicle_type: "car", open_issue_count: 0, created_at: now },
    ],
  });
  vi.mocked(adminDispatchApi.issues).mockResolvedValue([{ id: "i1", delivery_id: "d1", order_id: "o2", order_number: "CO-22",
    issue_type: "WRONG_ADDRESS", description: "Gate number doesn't exist", status: "OPEN", rider_first_name: "Sola",
    delivery_status: "assigned", has_photo: false, created_at: now }]);
  vi.mocked(adminDispatchApi.riders).mockResolvedValue([{ id: "p2", first_name: "Tayo", vehicle_type: "car", rating: 4.8 }]);
});
afterEach(cleanup);

describe("admin dispatch control centre", () => {
  it("shows legs, riders and issues, and only offers release/reassign before pickup", async () => {
    render(<Deliveries />);
    expect(await screen.findByText("VO-11")).toBeTruthy();
    expect(screen.getByText("Materials → tailor")).toBeTruthy();
    expect(screen.getByText("Wrong address")).toBeTruthy();
    const active = screen.getByRole("region", { name: "Active delivery assignments" });
    expect(within(active).getAllByRole("button", { name: "Release to job board" })).toHaveLength(1);
    expect(within(active).getByText(/Package collected/)).toBeTruthy();
  });

  it("requires a reason before releasing a rider", async () => {
    vi.mocked(adminDispatchApi.release).mockResolvedValue();
    render(<Deliveries />);
    fireEvent.click(await screen.findByRole("button", { name: "Release to job board" }));
    const confirm = screen.getByRole("button", { name: "Release rider" }) as HTMLButtonElement;
    expect(confirm.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Rider not responding" } });
    fireEvent.click(confirm);
    await waitFor(() => expect(adminDispatchApi.release).toHaveBeenCalledWith("d1", "Rider not responding"));
    await waitFor(() => expect(adminDispatchApi.board).toHaveBeenCalledTimes(2)); // refreshed after the action
  });

  it("reassigns to a chosen online rider", async () => {
    vi.mocked(adminDispatchApi.reassign).mockResolvedValue();
    render(<Deliveries />);
    fireEvent.click(await screen.findByRole("button", { name: "Reassign" }));
    fireEvent.change(screen.getByLabelText("New rider"), { target: { value: "p2" } });
    fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Closer rider available" } });
    fireEvent.click(screen.getByRole("button", { name: "Reassign rider" }));
    await waitFor(() => expect(adminDispatchApi.reassign).toHaveBeenCalledWith("d1", "p2", "Closer rider available"));
  });

  it("resolves an issue with a note and shows server errors", async () => {
    vi.mocked(adminDispatchApi.updateIssue).mockRejectedValueOnce(new Error("This issue is already closed."));
    render(<Deliveries />);
    fireEvent.click(await screen.findByRole("button", { name: "Resolve" }));
    fireEvent.change(screen.getByLabelText(/Resolution note/), { target: { value: "Customer shared the right gate" } });
    fireEvent.click(screen.getByRole("button", { name: "Resolve issue" }));
    expect((await screen.findByRole("alert")).textContent).toBe("This issue is already closed.");
    expect(adminDispatchApi.updateIssue).toHaveBeenCalledWith("i1", "RESOLVED", "Customer shared the right gate");
  });
});

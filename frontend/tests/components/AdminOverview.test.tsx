import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "@/pages/admin/Dashboard";
import { adminOperationsApi } from "@/api/admin-operations.api";
import { adminDispatchApi } from "@/api/admin-dispatch.api";
import { adminSecurityApi } from "@/api/admin-security.api";
import { verificationApi } from "@/api/verification.api";
import { dashboardApi } from "@/api/dashboard.api";

vi.mock("@/api/admin-operations.api", () => ({ adminOperationsApi: { operations: vi.fn(), orderExceptions: vi.fn() } }));
vi.mock("@/api/admin-dispatch.api", () => ({ adminDispatchApi: { board: vi.fn() } }));
vi.mock("@/api/admin-security.api", () => ({ adminSecurityApi: { summary: vi.fn() } }));
vi.mock("@/api/verification.api", () => ({ verificationApi: { queue: vi.fn() } }));
vi.mock("@/api/dashboard.api", () => ({ dashboardApi: { getCommerceSummary: vi.fn().mockRejectedValue(new Error("off")) } }));

const OPS = {
  marketplace: { customer: 120, tailor: 14, designer: 3, vendor: 9, delivery_partner: 7 },
  verification: {
    kyc_pending: [{ id: "k1", user_id: "u1", status: "pending", documents: ["d1"] }],
    kyb_pending: [{ id: "b1", owner_id: "u2", status: "pending", documents: ["d2"] }],
  },
  financial_controls: { production_payments_enabled: false, ledger_balanced: true },
  delivery_issues: [{ id: "i1", type: "CUSTOMER_UNREACHABLE", status: "OPEN" }],
  audit_events: [{ id: "a1", action: "admin.kyb.reviewed" }],
};
const BOARD = { unassigned_count: 2, active_count: 3, available_verified_riders: 4, open_issue_count: 1, auto_offers_enabled: false, pending: [], active: [] };
const check = (id: string, extra = {}) => ({
  id, status: "pending", submitted_at: "2026-11-06T09:12:00Z", applicant_name: "Adebayo Balogun", applicant_role: "vendor",
  documents: [], official_name: null, name_match: null, registry_checked: false, ...extra,
});

beforeEach(() => {
  vi.mocked(adminOperationsApi.operations).mockResolvedValue(OPS);
  vi.mocked(adminOperationsApi.orderExceptions).mockResolvedValue([
    { kind: "overdue", order_id: "o1", order_number: "TL-249E21", order_type: "customer_order", status: "in_production",
      seller_name: "Chidi Tailoring", item: "Senator", since: "2026-11-01T00:00:00Z", message: "Past the 7-day estimate by 1 day." },
    { kind: "vendor_no_confirm", order_id: "o2", order_number: "VO-3352", order_type: "vendor_order", status: "paid",
      seller_name: "Balogun Mart", item: "Aso oke", since: "2026-11-06T00:00:00Z", message: "Paid 26 h ago; the vendor hasn't confirmed stock." },
  ]);
  vi.mocked(adminDispatchApi.board).mockResolvedValue(BOARD);
  vi.mocked(adminSecurityApi.summary).mockResolvedValue({
    active_now: 3, sign_ins_24h: 40, failed_sign_ins_24h: 14, admin_sign_ins_24h: 1, distinct_ips_24h: 12,
    top_failed_ips: [{ ip_address: "203.0.113.9", attempts: 9 }], retention_days: 90,
  });
  vi.mocked(verificationApi.queue).mockImplementation(async (kind) => kind === "kyb"
    ? [check("b1", { business_name: "Balogun Mart" })]
    : [check("k1", { applicant_name: "Femi Ade", applicant_role: "delivery_partner", registry_checked: true, name_match: false, submitted_at: "2026-11-07T09:00:00Z" })]);
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("admin overview", () => {
  it("shows what needs a decision, from real counts, with links to where it's handled", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const attention = screen.getByRole("region", { name: "Needs your attention" });
    const tile = (name: string) => within(attention).getByText(name).closest("a")!;
    expect(await within(tile("Verification")).findByText("2")).toBeTruthy();
    expect(within(tile("Verification")).getByText("1 identity · 1 business")).toBeTruthy();
    expect(within(tile("No rider yet")).getByText("2")).toBeTruthy();
    expect(tile("No rider yet").getAttribute("href")).toBe("/app/admin/deliveries");
    expect(within(tile("Rider issues")).getByText("Customer unreachable")).toBeTruthy();
    expect(within(tile("Failed sign-ins (24 h)")).getByText("14")).toBeTruthy();
    expect(within(tile("Failed sign-ins (24 h)")).getByText("9 from one address")).toBeTruthy();
  });

  it("lists the oldest checks first with the registry result, and links to the existing review pages", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const queue = await screen.findByRole("region", { name: "Waiting for verification" });
    const rows = await within(queue).findAllByRole("listitem");
    expect(within(rows[0]).getByText("Balogun Mart")).toBeTruthy();
    expect(within(rows[0]).getByText("Check by hand")).toBeTruthy();
    expect(rows[0].querySelector("a")!.getAttribute("href")).toBe("/app/admin/kyb");
    expect(within(rows[1]).getByText("Femi Ade")).toBeTruthy();
    expect(within(rows[1]).getByText("Name mismatch")).toBeTruthy();
    expect(within(rows[1]).getByText(/Rider · identity \(NIN\)/)).toBeTruthy();
    // Reviewing happens on the existing pages; nothing on the overview approves or rejects.
    expect(screen.queryByRole("button", { name: /approve|reject/i })).toBeNull();
  });

  it("shows switches read-only and keeps working when one source fails", async () => {
    vi.mocked(adminDispatchApi.board).mockRejectedValue(new Error("403"));
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const switches = await screen.findByRole("region", { name: "Platform switches" });
    expect(within(switches).getByText("Payments").nextSibling?.textContent).toBe("Switched off");
    expect(within(switches).getByText("Balanced")).toBeTruthy();
    expect(within(switches).getByText("Couldn't load")).toBeTruthy();
    expect(within(switches).queryByRole("button")).toBeNull();
    const people = screen.getByRole("region", { name: "People" });
    expect(within(people).getByText("Riders").nextSibling?.textContent).toBe("7");
    expect(within(screen.getByRole("region", { name: "Needs your attention" })).getByText("No rider yet").closest("a")!.textContent).toMatch(/—Couldn't load/);
  });

  it("keeps the review queue and payments when the operations request fails, and offers a retry", async () => {
    vi.mocked(adminOperationsApi.operations).mockRejectedValue(new Error("down"));
    vi.mocked(dashboardApi.getCommerceSummary).mockResolvedValueOnce({ verified_count: 4, verified_volume_ngn: "120000", note: "Test mode." } as never);
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(await screen.findByText("Part of the overview couldn't load")).toBeTruthy();
    const queue = screen.getByRole("region", { name: "Waiting for verification" });
    expect(await within(queue).findByText("Balogun Mart")).toBeTruthy();
    expect(await screen.findByRole("region", { name: "Verified payments" })).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "Platform switches" })).getAllByText("Couldn't load")).toHaveLength(2);
    expect(screen.queryByRole("region", { name: "People" })).toBeNull();
  });

  it("refreshes every source, not just the operations counts", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    await screen.findByRole("region", { name: "Platform switches" });
    vi.mocked(adminDispatchApi.board).mockResolvedValue({ ...BOARD, unassigned_count: 5 });
    vi.mocked(adminSecurityApi.summary).mockRejectedValue(new Error("blip"));
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    const attention = screen.getByRole("region", { name: "Needs your attention" });
    expect(await within(within(attention).getByText("No rider yet").closest("a")!).findByText("5")).toBeTruthy();
    expect(adminDispatchApi.board).toHaveBeenCalledTimes(2);
    expect(adminSecurityApi.summary).toHaveBeenCalledTimes(2);
    expect(verificationApi.queue).toHaveBeenCalledTimes(4);
  });

  it("lists orders waiting too long or past their estimate", async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    const list = screen.getByRole("region", { name: "Orders needing attention" });
    const rows = await within(list).findAllByRole("listitem");
    expect(within(rows[0]).getByText("Overdue")).toBeTruthy();
    expect(within(rows[0]).getByText(/Chidi Tailoring · Past the 7-day estimate/)).toBeTruthy();
    expect(within(rows[1]).getByText("Vendor hasn't confirmed")).toBeTruthy();
  });
});

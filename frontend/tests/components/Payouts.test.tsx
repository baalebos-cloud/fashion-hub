import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PayoutAccountForm } from "@/components/payouts/PayoutAccountForm";
import { SellerPayoutList } from "@/components/payouts/SellerPayoutList";
import AdminPayouts from "@/pages/admin/Payouts";
import { payoutsApi } from "@/api/payouts.api";
import { verificationApi } from "@/api/verification.api";

vi.mock("@/api/payouts.api", () => ({
  payoutsApi: { banks: vi.fn(), account: vi.fn(), setAccount: vi.fn(), mine: vi.fn(), adminList: vi.fn(),
    adminHold: vi.fn(), adminRelease: vi.fn() },
}));
const reviewWindow = vi.hoisted(() => ({ open: false }));
vi.mock("@/api/verification.api", () => ({
  verificationApi: { openReviewWindow: vi.fn(async () => { reviewWindow.open = true; }) },
  hasReviewWindow: () => reviewWindow.open, endReviewWindow: () => { reviewWindow.open = false; }, stepUpHeaders: () => undefined,
}));
vi.mock("@/hooks/use-timezone", () => ({ useTimezone: () => "Africa/Lagos" }));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => { vi.clearAllMocks(); reviewWindow.open = false; });
afterEach(cleanup);

describe("payout bank account", () => {
  it("checks a new account with the bank, needing the password", async () => {
    vi.mocked(payoutsApi.account).mockResolvedValue({ account: null, payouts_enabled: true });
    vi.mocked(payoutsApi.banks).mockResolvedValue([{ code: "058", name: "Guaranty Trust Bank" }]);
    vi.mocked(payoutsApi.setAccount).mockResolvedValue({ bank_name: "Guaranty Trust Bank", account_last4: "6789",
      account_name: "ADA CHIOMA OBI", name_matches: true, verified_at: new Date().toISOString() });
    render(<PayoutAccountForm />);
    await screen.findByRole("option", { name: "Guaranty Trust Bank" });
    fireEvent.change(screen.getByLabelText("Bank"), { target: { value: "058" } });
    fireEvent.change(screen.getByLabelText("Account number"), { target: { value: "0123-456-789" } });
    const save = screen.getByRole("button", { name: "Check and save" }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Your Tailora password"), { target: { value: "secret" } });
    fireEvent.click(save);
    expect(await screen.findByText("ADA CHIOMA OBI")).toBeTruthy();
    expect(payoutsApi.setAccount).toHaveBeenCalledWith({ bank_code: "058", account_number: "0123456789", password: "secret" });
    expect(screen.getByText(/sent here automatically/)).toBeTruthy();
  });

  it("explains when the account name doesn't match", async () => {
    vi.mocked(payoutsApi.account).mockResolvedValue({ payouts_enabled: true, account: { bank_name: "Access Bank",
      account_last4: "1111", account_name: "TUNDE BAKARE", name_matches: false, verified_at: "" } });
    render(<PayoutAccountForm />);
    expect(await screen.findByText(/doesn't match your verified name/)).toBeTruthy();
  });
});

it("shows each payout's status and why one is held", async () => {
  vi.mocked(payoutsApi.mine).mockResolvedValue([
    { order_id: "o1", gross_amount: 10000, commission_amount: 1500, net_amount: 8500, currency: "NGN", status: "paid",
      hold_reason: null, paid_at: new Date().toISOString(), created_at: new Date().toISOString() },
    { order_id: "o2", gross_amount: 5000, commission_amount: 750, net_amount: 4250, currency: "NGN", status: "held",
      hold_reason: "A refund on this order is open or done.", paid_at: null, created_at: new Date().toISOString() },
  ]);
  render(<SellerPayoutList />);
  expect(await screen.findByText("Paid")).toBeTruthy();
  expect(screen.getByText("A refund on this order is open or done.")).toBeTruthy();
});

it("admins need an authenticator code to release a held payout", async () => {
  vi.mocked(payoutsApi.adminList).mockResolvedValue({ payouts_enabled: true, items: [{ id: "p1", status: "held",
    order_number: "TL-1", order_status: "received", seller_name: "Ada Obi", net_amount: 8500, currency: "NGN",
    hold_reason: "The bank account name doesn't match", failure_reason: null, attempts: 0, paid_at: null,
    created_at: new Date().toISOString() }] });
  vi.mocked(payoutsApi.adminRelease).mockResolvedValue();
  render(<AdminPayouts />);
  fireEvent.click(await screen.findByRole("button", { name: "Release" }));
  expect(payoutsApi.adminRelease).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Code from your authenticator app"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm and release" }));
  await waitFor(() => expect(payoutsApi.adminRelease).toHaveBeenCalledWith("p1"));
  expect(verificationApi.openReviewWindow).toHaveBeenCalledWith("123456");
});

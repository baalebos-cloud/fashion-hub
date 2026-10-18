import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PaymentSuccess from "@/pages/customer/PaymentSuccess";
import { paymentsApi } from "@/api/payments.api";
import type { Payment } from "@/types/payment";

vi.mock("@/api/payments.api", () => ({ paymentsApi: { verify: vi.fn() } }));
const verify = vi.mocked(paymentsApi.verify);
function payment(status: Payment["status"]): Payment {
  return { id: "payment", order_id: "order", provider: "paystack", provider_reference: "saved-reference", amount: 100, currency: "NGN", status };
}
function open(query: string) {
  render(<MemoryRouter initialEntries={[`/payment/success${query}`]}><PaymentSuccess /></MemoryRouter>);
}
afterEach(cleanup);
beforeEach(() => vi.resetAllMocks());
describe("payment callback", () => {
  it("ignores a claimed success without a payment reference", () => {
    open("?status=successful");
    expect(verify).not.toHaveBeenCalled();
    expect(screen.queryByText("Payment successful")).toBeNull();
    expect(screen.getByText(/No payment reference/)).toBeTruthy();
  });
  it("waits for server verification before showing success", async () => {
    let resolve!: (result: Payment) => void;
    verify.mockReturnValue(new Promise((done) => { resolve = done; }));
    open("?reference=saved-reference&status=successful");
    expect(screen.queryByText("Payment successful")).toBeNull();
    resolve(payment("successful"));
    await screen.findByText("Payment successful");
    expect(verify).toHaveBeenCalledWith("saved-reference");
  });
  it("shows pending and verifies again on retry", async () => {
    verify.mockResolvedValueOnce(payment("pending")).mockResolvedValueOnce(payment("successful"));
    open("?tx_ref=saved-reference&status=successful");
    await screen.findByText(/payment status is pending/);
    expect(screen.queryByText("Payment successful")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Check payment again" }));
    await screen.findByText("Payment successful");
    expect(verify).toHaveBeenCalledTimes(2);
  });
  it("shows a received payment needing review without claiming a confirmed order", async () => {
    verify.mockResolvedValue({ ...payment("successful"), requires_review: true });
    open("?reference=saved-reference");
    await screen.findByText("Payment received — review required");
    expect(screen.queryByText("Payment successful")).toBeNull();
    expect(screen.getByText(/Contact support with reference/)).toBeTruthy();
  });
  it("offers a retry after a verification error", async () => {
    verify.mockRejectedValueOnce(new Error("Provider unavailable")).mockResolvedValueOnce(payment("failed"));
    open("?trxref=saved-reference");
    await waitFor(() => expect((screen.getByRole("button", { name: "Check payment again" }) as HTMLButtonElement).disabled).toBe(false));
    expect(screen.queryByText("Payment successful")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Check payment again" }));
    await screen.findByText(/payment status is failed/);
  });
});

import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { OrderDispute } from "@/components/orders/OrderDispute";
import AdminDisputes from "@/pages/admin/Disputes";
import { disputesApi } from "@/api/disputes.api";
import { verificationApi } from "@/api/verification.api";

vi.mock("@/api/disputes.api", async (orig) => ({
  ...(await orig<typeof import("@/api/disputes.api")>()),
  disputesApi: { open: vi.fn(), forOrder: vi.fn(), adminList: vi.fn(), resolve: vi.fn() },
}));
vi.mock("@/api/verification.api", () => ({
  verificationApi: { openReviewWindow: vi.fn() }, hasReviewWindow: () => false, endReviewWindow: vi.fn(), stepUpHeaders: () => undefined,
}));

const dispute = { id: "d1", order_id: "o1", status: "open" as const, reason: "wrong_size" as const, reason_label: "Wrong size or fit",
  description: "Trousers 5 cm too short.", outcome: null, outcome_label: null, resolution_note: null, refund_amount: null,
  created_at: "2026-11-15T09:00:00Z", resolved_at: null, order_number: "CO-1", order_type: "customer_order", order_total: 50000,
  currency: "NGN", buyer_name: "Amaka", seller_name: "Adire Studio" };

beforeEach(() => vi.clearAllMocks());

it("the buyer reports a problem on a paid order", async () => {
  vi.mocked(disputesApi.forOrder).mockResolvedValue([]);
  vi.mocked(disputesApi.open).mockResolvedValue(dispute);
  render(<OrderDispute orderId="o1" orderStatus="delivered" isBuyer />);
  fireEvent.click(await screen.findByRole("button", { name: "Report a problem" }));
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "wrong_size" } });
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Trousers 5 cm too short." } });
  fireEvent.click(screen.getByRole("button", { name: "Send to Tailora" }));
  expect(await screen.findByText(/Being reviewed by Tailora/)).toBeTruthy();
  expect(disputesApi.open).toHaveBeenCalledWith("o1", "wrong_size", "Trousers 5 cm too short.");
});

it("nothing to report on an unpaid order", async () => {
  vi.mocked(disputesApi.forOrder).mockResolvedValue([]);
  const { container } = render(<OrderDispute orderId="o1" orderStatus="pending" isBuyer />);
  await waitFor(() => expect(disputesApi.forOrder).toHaveBeenCalled());
  expect(container.textContent).toBe("");
});

it("admin refunds after entering the authenticator code", async () => {
  vi.mocked(disputesApi.adminList).mockResolvedValue({ total: 1, page: 1, page_size: 50, items: [dispute] });
  vi.mocked(disputesApi.resolve).mockResolvedValue({ ...dispute, status: "resolved" });
  render(<MemoryRouter><AdminDisputes /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Decide" }));
  fireEvent.click(screen.getByLabelText(/^Refund/));
  fireEvent.change(screen.getByPlaceholderText(/Measurements on the order/), { target: { value: "Not delivered; full refund." } });
  fireEvent.click(screen.getByRole("button", { name: "Resolve dispute" }));
  fireEvent.change(await screen.findByLabelText("Code from your authenticator app"), { target: { value: "123456" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm with code" }));
  await waitFor(() => expect(disputesApi.resolve).toHaveBeenCalledWith("d1", { outcome: "refund", note: "Not delivered; full refund.", refund_amount: "50000" }));
  expect(verificationApi.openReviewWindow).toHaveBeenCalledWith("123456");
});

it("admin list pages through more than 50 disputes", async () => {
  vi.mocked(disputesApi.adminList).mockResolvedValue({ total: 120, page: 1, page_size: 50, items: [dispute] });
  render(<MemoryRouter><AdminDisputes /></MemoryRouter>);
  expect(await screen.findByText("(120)")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /next/i }));
  await waitFor(() => expect(disputesApi.adminList).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, page_size: 50 })));
});

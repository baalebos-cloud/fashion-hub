import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DeliveryHistory from "@/pages/delivery/DeliveryHistory";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery } from "@/types/delivery";

vi.mock("@/api/deliveries.api", () => ({ deliveriesApi: { myHistory: vi.fn() } }));

const page = (n: number, size = 20): Delivery[] => Array.from({ length: size }, (_, i) => ({
  id: `p${n}-${i}`, order_id: `order${n}${i}aaaaaaa`, status: "delivered", delivery_fee: 1000, delivered_at: "2026-11-15T09:00:00Z",
}));

beforeEach(() => vi.clearAllMocks());

it("retries a page that failed instead of skipping to the next one", async () => {
  vi.mocked(deliveriesApi.myHistory)
    .mockResolvedValueOnce(page(1))
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(page(2, 3));
  render(<MemoryRouter><DeliveryHistory /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "Show older deliveries" }));
  fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
  await screen.findAllByText(/Order ORDER22/);
  expect(vi.mocked(deliveriesApi.myHistory).mock.calls.map((c) => c[0])).toEqual([1, 2, 2]);
  expect(screen.queryByRole("button", { name: "Show older deliveries" })).toBeNull(); // last page was short
});

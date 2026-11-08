import { describe, expect, it, vi } from "vitest";
import { ordersApi } from "@/api/orders.api";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn() } }));

describe("ordersApi.listAll", () => {
  it("keeps fetching pages until one comes back short, so totals include older orders", async () => {
    const page = (n: number, size: number) => Array.from({ length: size }, (_, i) => ({ id: `${n}-${i}` }));
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({ data: page(1, 100) })
      .mockResolvedValueOnce({ data: page(2, 100) })
      .mockResolvedValueOnce({ data: page(3, 7) });
    const all = await ordersApi.listAll({ perspective: "selling", order_type: "customer_order" });
    expect(all).toHaveLength(207);
    expect(vi.mocked(apiClient.get).mock.calls.map((c) => (c[1] as { params: { page: number } }).params.page)).toEqual([1, 2, 3]);
    expect((vi.mocked(apiClient.get).mock.calls[0][1] as { params: object }).params)
      .toEqual({ perspective: "selling", order_type: "customer_order", page: 1, page_size: 100 });
  });
});

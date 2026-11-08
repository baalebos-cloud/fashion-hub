import { describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useLowStockThreshold } from "@/hooks/use-low-stock-threshold";
import { vendorsApi } from "@/api/vendors.api";

vi.mock("@/api/vendors.api", () => ({ vendorsApi: { mine: vi.fn(), setStockAlert: vi.fn() } }));

describe("low stock level", () => {
  it("keeps a saved level when the first load answers late", async () => {
    let answer!: (v: unknown) => void;
    vi.mocked(vendorsApi.mine).mockReturnValue(new Promise((r) => { answer = r; }) as never);
    vi.mocked(vendorsApi.setStockAlert).mockResolvedValue({ low_stock_threshold: 25 } as never);
    const { result } = renderHook(() => useLowStockThreshold());
    await act(async () => { await result.current.save(25); });
    expect(result.current.threshold).toBe(25);
    await act(async () => { answer({ low_stock_threshold: 10 }); });
    await waitFor(() => expect(result.current.threshold).toBe(25));
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";
import { professionalsApi } from "@/api/professionals.api";
import { apiClient } from "@/lib/api/client";
import { rankingBrowserId, setBrowserOptOut } from "@/lib/tracking/interactions";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn().mockResolvedValue({ data: { items: [] } }) } }));
const params = () => vi.mocked(apiClient.get).mock.calls.at(-1)?.[1]?.params;

beforeEach(() => { localStorage.clear(); setBrowserOptOut(false); });

describe("tailor search ranking", () => {
  it("asks for personal ranking only from search pages", async () => {
    await professionalsApi.list({ pageSize: 50 });
    expect(params()).toMatchObject({ ranked: undefined, browser_id: undefined });
    await professionalsApi.list({ ranked: true, browserId: "b-1" });
    expect(params()).toMatchObject({ ranked: true, browser_id: "b-1" });
  });

  it("sends no browser ID once this browser opted out", () => {
    expect(rankingBrowserId()).toBeTruthy();
    setBrowserOptOut(true);
    expect(rankingBrowserId()).toBeUndefined();
  });
});

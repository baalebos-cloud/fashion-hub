import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SmartDesignSearch } from "@/components/search/SmartDesignSearch";
import { searchApi } from "@/api/search.api";

vi.mock("@/api/search.api", () => ({ searchApi: { smart: vi.fn() } }));
vi.mock("@/lib/tracking/interactions", () => ({ trackSearch: vi.fn() }));
afterEach(cleanup);

const renderSearch = () => render(
  <MemoryRouter><SmartDesignSearch profilePathFor={(id) => `/tailors/${id}`} /></MemoryRouter>);

function search(text: string) {
  fireEvent.change(screen.getByLabelText("Describe what you want"), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "Search designs" }));
}

describe("smart design search", () => {
  it("shows what it understood and links results to the tailor", async () => {
    vi.mocked(searchApi.smart).mockResolvedValue({
      understood_by: "ai", filters: { keywords: ["agbada", "blue"], min_price: null, max_price: 50000 },
      designs: [{ id: "d1", professional_id: "p1", professional_name: "Kemi Couture", title: "Blue agbada",
        description: null, base_price: 45000, currency: "NGN", is_published: true }],
    });
    renderSearch();
    search("blue agbada under 50k");
    expect(await screen.findByText("Blue agbada")).toBeTruthy();
    expect(screen.getByText("agbada")).toBeTruthy();
    expect(screen.getByText(/Up to/)).toBeTruthy();
    expect(screen.getByText(/understood by AI/)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Blue agbada/ }).getAttribute("href")).toBe("/tailors/p1?from=smart_search");
  });

  it("asks for more detail when nothing was understood", async () => {
    vi.mocked(searchApi.smart).mockResolvedValue({
      understood_by: "keywords", filters: { keywords: [], min_price: null, max_price: null }, designs: [] });
    renderSearch();
    search("please show me");
    expect(await screen.findByText(/Add a garment, fabric, colour or budget/)).toBeTruthy();
  });

  it("says when search is unavailable", async () => {
    vi.mocked(searchApi.smart).mockRejectedValue(new Error("down"));
    renderSearch();
    search("lace buba");
    expect(await screen.findByRole("alert")).toBeTruthy();
  });
});

import { beforeEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Vendors from "@/pages/admin/Vendors";
import Favorites from "@/pages/customer/Favorites";
import { adminListsApi } from "@/api/admin-lists.api";
import { favoritesApi } from "@/api/favorites.api";

vi.mock("@/api/admin-lists.api", () => ({ adminListsApi: { vendors: vi.fn() } }));
vi.mock("@/api/favorites.api", () => ({ favoritesApi: { list: vi.fn(), toggle: vi.fn() } }));

beforeEach(() => vi.clearAllMocks());

it("admin vendors list loads real rows and filters", async () => {
  vi.mocked(adminListsApi.vendors).mockResolvedValue({ total: 1, page: 1, page_size: 50, items: [{
    id: "v1", business_name: "Balogun Fabrics", owner_name: "Adebayo Balogun", owner_email: "b@example.com",
    is_verified: false, average_rating: 0, active_products: 3, created_at: "2026-11-01T00:00:00Z" }] });
  render(<MemoryRouter><Vendors /></MemoryRouter>);
  expect(await screen.findByText("Balogun Fabrics")).toBeTruthy();
  expect(screen.getAllByText("Awaiting verification").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "Verified" }));
  await waitFor(() => expect(adminListsApi.vendors).toHaveBeenLastCalledWith(expect.objectContaining({ verified: true, page: 1 })));
});

it("favorites shows saved items with links and can remove one", async () => {
  vi.mocked(favoritesApi.list).mockResolvedValue([
    { id: "f1", favorite_type: "professional", favorite_ref_id: "p1", title: "Adire Studio", subtitle: "Tailor", image_url: null,
      price: null, currency: null, professional_id: "p1", available: true },
    { id: "f2", favorite_type: "vendor_product", favorite_ref_id: "pr1", title: "French lace", subtitle: "Balogun Fabrics",
      image_url: null, price: 9500, currency: "NGN", professional_id: null, available: false },
  ]);
  vi.mocked(favoritesApi.toggle).mockResolvedValue(false);
  render(<MemoryRouter><Favorites /></MemoryRouter>);
  const studio = await screen.findByText("Adire Studio");
  expect(studio.closest("a")?.getAttribute("href")).toBe("/app/customer/professionals/p1");
  expect(screen.getByText("Not available right now")).toBeTruthy();
  expect(screen.getByText("French lace").closest("a")).toBeNull(); // unavailable: not a link
  fireEvent.click(screen.getByRole("button", { name: "Remove Adire Studio from favorites" }));
  await waitFor(() => expect(screen.queryByText("Adire Studio")).toBeNull());
  expect(favoritesApi.toggle).toHaveBeenCalledWith("professional", "p1");
});

import { expect, test } from "@playwright/test";

const shop = {
  handle: "kemi-couture", share_url: "http://127.0.0.1:4173/s/kemi-couture", kind: "tailor",
  professional_id: "pro-1", display_name: "Kemi Couture",
  bio: "Bespoke agbada, kaftans and aso-ebi for weddings across Lagos.", is_verified: true,
  average_rating: 4.6, review_count: 12, years_experience: 8, accepts_new_orders: true,
  area: "Ikeja, Lagos", member_since: 2025, profile_photo_url: null,
  designs: [
    { id: "d1", title: "Wedding agbada", base_price: 85000, currency: "NGN", estimated_turnaround_days: 10 },
    { id: "d2", title: "Senator kaftan", base_price: 42000, currency: "NGN", estimated_turnaround_days: 6 },
    { id: "d3", title: "Aso-ebi iro and buba", base_price: 55000, currency: "NGN", estimated_turnaround_days: null },
  ],
  products: [], portfolio: [],
  reviews: [{ id: "r1", reviewer_first_name: "Ada", score: 5, comment: "Perfect fit, delivered early.", created_at: "2026-10-01" }],
};

for (const viewport of [{ width: 390, height: 844 }, { width: 1280, height: 900 }]) {
  test(`storefront link renders without horizontal scroll at ${viewport.width}px`, async ({ page }, info) => {
    await page.setViewportSize(viewport);
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/storefronts/kemi-couture")) return route.fulfill({ json: shop });
      return route.fulfill({ status: 401, json: { error: { message: "unauthenticated", code: "unauthorized" } } });
    });
    await page.goto("/s/kemi-couture");
    await expect(page.getByRole("heading", { name: "Kemi Couture" })).toBeVisible();
    await expect(page.getByText("Wedding agbada")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({ path: info.outputPath(`storefront-${viewport.width}.png`), fullPage: true });
  });
}

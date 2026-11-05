import { expect, test } from "@playwright/test";

test("a recipient opens a shared tracking link on a phone without an account", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    if (path.startsWith("/public/track/")) return route.fulfill({ json: {
      tracking_number: "TL-20431", seller_name: "Kemi Couture", kind: "garment", status: "out_for_delivery",
      delivery_status: "in_transit", dropoff_area: "Lekki, Lagos", eta_minutes: 12, eta_basis: "live_gps_estimate",
      rider: { first_name: "Sola", vehicle_type: "bike", is_verified: true, rating: 4.8 },
      link_expires_at: new Date(Date.now() + 2 * 864e5).toISOString(),
      milestones: [["placed", "Order placed", "2026-11-01T10:00:00Z", "done"], ["ready", "Ready for pickup", "2026-11-05T09:40:00Z", "done"],
        ["rider_assigned", "Rider assigned: Sola", "2026-11-05T09:47:00Z", "done"], ["picked_up", "Picked up by rider", "2026-11-05T10:15:00Z", "done"],
        ["delivered", "Delivered", null, "current"]].map(([key, label, at, state]) => ({ key, label, at, state })) } });
    return route.fulfill({ status: 401, json: { error: { code: "unauthorized", message: "Sign in" } } });
  });
  await page.goto("/track/" + "t".repeat(43));
  await expect(page.getByRole("heading", { name: "On its way" })).toBeVisible();
  await expect(page.getByText("12 min")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: info.outputPath("public-tracking-390.png"), fullPage: true });
});

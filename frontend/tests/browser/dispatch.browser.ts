import { expect, test, type Page } from "@playwright/test";

const user = (role: string) => ({ id: "u1", role, email: "u@example.com", full_name: "Sola Bello", is_active: true, timezone: "Africa/Lagos" });
const soon = () => new Date(Date.now() + 8 * 60_000).toISOString();

async function mockApi(page: Page, role: string, extra: (path: string) => unknown) {
  await page.addInitScript(() => sessionStorage.setItem("tailora.access_token", "browser-test"));
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    if (path === "/users/me") return route.fulfill({ json: user(role) });
    const body = extra(path);
    if (body !== undefined) return route.fulfill({ json: body });
    return route.fulfill({ json: path === "/notifications" ? { items: [] } : [] });
  });
}

test("rider job board shows priced jobs and an offer form on a phone", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page, "delivery_partner", (path) => path === "/delivery-requests/available" ? [
    { id: "r1", order_id: "o1", status: "requested", suggested_fare: 3600, currency: "NGN", offer_min: 2900,
      offer_max: 7200, approx_road_km: 20.5, pickup_area: "Ikeja, Lagos", dropoff_area: "Victoria Island, Lagos",
      posted_at: new Date(Date.now() - 4 * 60_000).toISOString(), my_offer: null },
    { id: "r2", order_id: "o2", status: "requested", suggested_fare: 1500, currency: "NGN", offer_min: 1200,
      offer_max: 3000, approx_road_km: 6.1, pickup_area: "Yaba, Lagos", dropoff_area: "Surulere, Lagos",
      posted_at: new Date(Date.now() - 60_000).toISOString(),
      my_offer: { id: "f1", amount: 1800, status: "pending", eta_to_pickup_minutes: 9, expires_at: soon() } },
  ] : path === "/delivery-partners/me" ? { id: "p1", is_verified: true, is_available: true, vehicle_type: "bike" } : undefined);
  await page.goto("/app/delivery/requests");
  await expect(page.getByText("₦3,600", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Offer your fare" }).click();
  await expect(page.getByLabel("Your fare (₦)").first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: info.outputPath("rider-jobs-390.png"), fullPage: true });
});

test("customer sees the delivery journey with a live ETA on a phone", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const order = { id: "o1", order_number: "TL-20431", order_type: "customer_order", buyer_user_id: "u1", seller_user_id: "t1",
    status: "out_for_delivery", currency: "NGN", total_amount: 85000, subtotal: 85000, delivery_fee: 3600, tax_amount: 0,
    discount_amount: 0, ordered_at: "2026-11-01T10:00:00Z", items: [] };
  await mockApi(page, "customer", (path) => {
    if (path === "/orders/o1") return order;
    if (path === "/orders/o1/timeline") return [];
    if (path === "/deliveries/orders/o1/journey") return {
      order_id: "o1", tracking_number: "TL-20431", status: "out_for_delivery", delivery_status: "in_transit",
      live: { eta_minutes: 14, distance_remaining_km: 4.2, basis: "live_gps_estimate", updated_at: null },
      milestones: [
        ["placed", "Order placed", "2026-11-01T10:00:00Z", "done"], ["paid", "Payment confirmed", "2026-11-01T10:02:00Z", "done"],
        ["accepted", "Accepted by your tailor", "2026-11-01T12:30:00Z", "done"], ["in_production", "Being made", "2026-11-02T09:00:00Z", "done"],
        ["ready", "Ready for pickup", "2026-11-05T09:40:00Z", "done"], ["dispatch_requested", "Looking for a rider", "2026-11-05T09:41:00Z", "done"],
        ["rider_assigned", "Rider assigned: Sola", "2026-11-05T09:47:00Z", "done"], ["picked_up", "Picked up by rider", "2026-11-05T10:15:00Z", "done"],
        ["delivered", "Delivered", null, "current"], ["received", "Received and confirmed", null, "upcoming"],
      ].map(([key, label, at, state]) => ({ key, label, at, state })) };
    if (path === "/deliveries/orders/o1/tracking") return null;
    if (path === "/calls/orders/o1/contacts") return [];
    return undefined;
  });
  await page.goto("/app/customer/orders/o1");
  const journey = page.getByRole("region", { name: "Delivery journey" });
  await expect(journey.getByText("14 min")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await journey.screenshot({ path: info.outputPath("journey-390.png") });
});

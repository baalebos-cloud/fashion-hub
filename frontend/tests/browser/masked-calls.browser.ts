import { expect, test } from "@playwright/test";

test("customer calls their tailor in the app without seeing any number", async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => sessionStorage.setItem("tailora.access_token", "browser-test"));
  const order = { id: "o1", order_number: "TL-20431", order_type: "customer_order", buyer_user_id: "c1",
    seller_user_id: "t1", status: "in_production", currency: "NGN", total_amount: 85000, subtotal: 85000,
    delivery_fee: 0, tax_amount: 0, discount_amount: 0, ordered_at: "2026-11-01T10:00:00Z",
    items: [{ id: "i1", reference_type: "design", name_snapshot: "Wedding agbada", quantity: 1, unit_price: 85000, line_total: 85000 }] };
  let cancelled = false;
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    if (path === "/users/me") return route.fulfill({ json: { id: "c1", role: "customer", email: "c@example.com", full_name: "Ada Obi", is_active: true, timezone: "Africa/Lagos" } });
    if (path === "/orders/o1") return route.fulfill({ json: order });
    if (path === "/orders/o1/timeline") return route.fulfill({ json: [] });
    if (path === "/calls/orders/o1/contacts") return route.fulfill({ json: [
      { party: "seller", display_name: "Kemi Couture", available: true, reason: null }] });
    if (path === "/calls/app") return route.fulfill({ status: 201, json: {
      call_id: "c", status: "ringing", order_id: "o1", order_number: "TL-20431", other_party_name: "Kemi Couture",
      you_are: "caller", started_at: null, answered_at: null, token: "browser-test", url: "ws://127.0.0.1:9" } });
    if (path === "/calls/app/c/cancel") { cancelled = true; return route.fulfill({ json: { call_id: "c", status: "cancelled",
      order_id: "o1", order_number: "TL-20431", other_party_name: "Kemi Couture", you_are: "caller", started_at: null, answered_at: null } }); }
    if (path === "/deliveries/orders/o1/tracking") return route.fulfill({ json: null });
    return route.fulfill({ json: path === "/notifications" ? { items: [] } : [] });
  });

  await page.goto("/app/customer/orders/o1");
  const panel = page.getByRole("region", { name: "Contact about this order" });
  await expect(panel).toBeVisible();
  await panel.getByRole("button", { name: "Call" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Kemi Couture" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("calling-390.png") });
  // The test has no call server, so joining fails: the app must cancel the call and say so.
  await expect(dialog.getByText(/Couldn't connect the call|microphone/)).toBeVisible({ timeout: 15000 });
  expect(cancelled).toBe(true);
  expect(await page.evaluate(() => document.body.textContent?.match(/\+?234\d{6,}|0\d{10}/) ?? null)).toBeNull();
  expect(await page.locator('a[href^="tel:"]').count()).toBe(0);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await panel.screenshot({ path: info.outputPath("contacts-390.png") });
});

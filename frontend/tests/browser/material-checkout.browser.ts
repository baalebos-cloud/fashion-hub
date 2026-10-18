import { expect, test } from "@playwright/test";

test("a material order is reviewed separately and a late payment shows review required", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("fashionhub.access_token", "browser-test"));
  const expiry = new Date(Date.now() + 15 * 60000).toISOString();
  const cart = { cart_id: "cart", revision: 2, currency: "NGN", subtotal: 75, items: [
    { id: "a", product_variant_id: "variant-a", vendor_id: "store-a", vendor_name: "Cotton Store", product_name: "Cotton", sku: "A", currency: "NGN", quantity: 1, unit_price_snapshot: 25, is_available: true },
    { id: "b", product_variant_id: "variant-b", vendor_id: "store-b", vendor_name: "Silk Store", product_name: "Silk", sku: "B", currency: "NGN", quantity: 1, unit_price_snapshot: 50, is_available: true },
  ] };
  const order = { id: "order", order_number: "VO-BROWSER", order_type: "vendor_order", buyer_user_id: "buyer", seller_user_id: "seller", status: "checkout",
    currency: "NGN", total_amount: 27, subtotal: 27, delivery_fee: 0, tax_amount: 0, discount_amount: 0, reservation_expires_at: expiry,
    items: [{ id: "item", reference_type: "product_variant", name_snapshot: "Cotton (A)", quantity: 1, unit_price: 27, line_total: 27 }] };
  let checkoutBody: Record<string, unknown> | null = null;
  let initialized = 0;
  const unexpected: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    let body: unknown;
    if (path === "/users/me") body = { id: "buyer", role: "tailor", email: "test@example.com", full_name: "Test Buyer", is_active: true, timezone: "Africa/Lagos" };
    else if (path === "/carts/summary") body = cart;
    else if (path === "/addresses") body = [{ id: "address", label: "Home", formatted_address: "10 Street", city: "Lagos", country: "NG" }];
    else if (path === "/notifications") body = { items: [] };
    else if (path === "/checkout") { checkoutBody = route.request().postDataJSON(); body = order; }
    else if (path === "/orders/order") body = order;
    else if (path === "/orders/order/timeline") body = [];
    else if (path === "/payments") { initialized++; body = {}; }
    else if (path === "/payments/late-reference/verify") body = { id: "payment", order_id: "order", status: "successful", requires_review: true, provider_reference: "late-reference" };
    else { unexpected.push(path); body = {}; }
    await route.fulfill({ json: body });
  });
  await page.goto("/app/professional/checkout");
  await expect(page.getByRole("heading", { name: "Checkout materials" })).toBeVisible();
  await expect(page.getByLabel("Vendor")).toHaveValue("store-a");
  await page.getByRole("button", { name: "Create order and review total" }).click();
  await expect(page.getByRole("heading", { name: "VO-BROWSER" })).toBeVisible();
  expect(checkoutBody).toMatchObject({ cart_id: "cart", cart_revision: 2, vendor_id: "store-a", delivery_address_id: "address" });
  expect(checkoutBody).not.toHaveProperty("total_amount");
  expect(initialized).toBe(0);
  await expect(page.getByText(/Final total:/)).toContainText("27.00");
  await expect(page.getByRole("button", { name: "Pay now" })).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(page.getByRole("button", { name: "Pay now" })).toBeEnabled();
  await page.goto("/app/professional/vendor-payment/success?reference=late-reference&status=successful");
  await expect(page.getByRole("heading", { name: "Payment received — review required" })).toBeVisible();
  await expect(page.getByText("Payment successful", { exact: true })).toHaveCount(0);
  expect(initialized).toBe(0);
  expect(unexpected).toEqual([]);
});

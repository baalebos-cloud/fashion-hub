import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, role: string, routes: Record<string, unknown>) {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => sessionStorage.setItem("tailora.access_token", "browser-test"));
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    if (path === "/users/me") return route.fulfill({ json: { id: "u1", role, email: "u@example.com", full_name: "Bisi Ola", is_active: true, timezone: "Africa/Lagos" } });
    if (path in routes) return route.fulfill({ json: routes[path] });
    if (path === "/kyb/status" || path === "/kyc/status") return route.fulfill({ status: 404, json: { error: { message: "none", code: "not_found" } } });
    return route.fulfill({ json: path === "/notifications" ? { items: [] } : [] });
  });
}

test("vendor sees a clear verification checklist on a phone", async ({ page }, info) => {
  await signIn(page, "vendor", { "/verification/me": {
    role: "vendor", verified: false, next_step: "Fix the item marked 'Needs attention' and resubmit.",
    steps: [
      { key: "identity", title: "Identity (NIN)", required: true, status: "verified", rejection_reason: null, submitted_at: null, action: "kyc" },
      { key: "business", title: "Business registration (CAC)", required: true, status: "rejected",
        rejection_reason: "The certificate photo is cut off at the bottom.", submitted_at: null, action: "kyb" },
    ] } });
  await page.goto("/app/vendor/verification");
  await expect(page.getByText("1 of 2 required checks complete")).toBeVisible();
  await expect(page.getByLabel("CAC registration number")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: info.outputPath("vendor-verification-390.png"), fullPage: true });
});

test("admin reviews a KYB submission with registry results on a phone", async ({ page }, info) => {
  await signIn(page, "admin", { "/admin/verifications": [{
    id: "k1", status: "pending", submitted_at: new Date(Date.now() - 3_600_000).toISOString(), applicant_name: "Bisi Ola",
    applicant_role: "vendor", documents: [{ id: "d1", type: "business_registration" }],
    official_name: "FABRIC HUB LIMITED", name_match: true, registry_checked: true, business_name: "Fabric Hub", registration: "RC 1234567" }] });
  await page.goto("/app/admin/kyb");
  await expect(page.getByText("FABRIC HUB LIMITED")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: info.outputPath("admin-kyb-390.png"), fullPage: true });
});

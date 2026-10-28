import { expect, test } from "@playwright/test";

/** Exercise the real app root so pages cannot silently omit providers. */
for (const path of ["/", "/login", "/signup", "/marketplace", "/find-a-tailor", "/forgot-password"]) {
  test("public route " + path + " mounts without missing contexts", async ({ page }) => {
    const fatal: string[] = [];
    page.on("pageerror", (error) => fatal.push(error.message));
    await page.goto(path);
    await expect(page.locator("#root")).not.toBeEmpty();
    await expect(page.getByText("Unexpected Application Error!")).toHaveCount(0);
    await expect(page.getByText("useToast must be used within")).toHaveCount(0);
    expect(fatal).toEqual([]);
  });
}

test("unknown route offers a usable home link instead of the default debug screen", async ({ page }) => {
  await page.goto("/missing-fashion-hub-page");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  await page.getByRole("link", { name: "Go to homepage" }).click();
  await expect(page).toHaveURL("/");
});


test("public marketplace shows a retry message instead of throwing on API outages", async ({ page }) => {
  const fatal: string[] = [];
  page.on("pageerror", (error) => fatal.push(error.message));
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Temporarily unavailable"}' })
  );
  await page.goto("/marketplace");
  await expect(page.getByRole("alert")).toContainText("marketplace information couldn't be loaded");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  expect(fatal).toEqual([]);
});

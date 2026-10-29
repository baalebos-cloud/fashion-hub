import { expect, test } from "@playwright/test";

for (const viewport of [{ width: 1280, height: 900 }, { width: 375, height: 812 }]) {
  test(`login retains its theme and focus at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    // Font availability must not determine whether the application is usable.
    await page.route("https://fonts.googleapis.com/**", (route) => route.abort());
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    const email = page.getByLabel("Email address", { exact: true });
    await expect(email).toHaveCSS("background-color", "rgb(250, 249, 245)");
    await expect(email).toHaveCSS("border-top-color", "rgb(217, 210, 193)");
    await expect(email).toHaveCSS("border-radius", "8px");
    const button = page.getByRole("button", { name: "Sign in" });
    await expect(button).toHaveCSS("background-color", "rgb(28, 34, 48)");
    await expect(button).toHaveCSS("color", "rgb(250, 249, 245)");
    await email.focus();
    await page.keyboard.press("Tab");
    const password = page.getByLabel("Password", { exact: true });
    await expect(password).toBeFocused();
    await expect(password).toHaveCSS("outline-style", "solid");
    await expect(password).toHaveCSS("outline-width", "2px");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

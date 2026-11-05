import { expect, test } from "@playwright/test";

const jpeg = Buffer.concat([Buffer.from("ffd8ffe000104a464946", "hex"), Buffer.alloc(256)]);

for (const viewport of [{ width: 390, height: 844 }, { width: 1280, height: 900 }]) {
  test(`customer drafts measurements from photos at ${viewport.width}px`, async ({ page }, info) => {
    await page.setViewportSize(viewport);
    await page.addInitScript(() => sessionStorage.setItem("tailora.access_token", "browser-test"));
    let analyzeCalls = 0;
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
      if (path === "/users/me") return route.fulfill({ json: { id: "c1", role: "customer", email: "c@example.com", full_name: "Ada Obi", is_active: true, timezone: "Africa/Lagos" } });
      if (path === "/measurements") return route.fulfill({ json: [] });
      if (path === "/ai/measurements/analyze") {
        analyzeCalls++;
        return route.fulfill({ json: {
          fields: [
            { field_name: "chest", value: 98.5, unit: "cm", source: "estimate", confidence: 0.55 },
            { field_name: "waist", value: 82, unit: "cm", source: "tape", confidence: 0.92 },
            { field_name: "hip", value: 101, unit: "cm", source: "estimate", confidence: 0.5 },
            { field_name: "shoulder_width", value: 44, unit: "cm", source: "estimate", confidence: 0.45 },
          ],
          notes: "Fitted clothing and a straight posture give the best results.",
          photo_issues: ["Arms are close to the body"], provider: "vertex_ai", requires_review: true,
        } });
      }
      if (path === "/notifications") return route.fulfill({ json: { items: [] } });
      return route.fulfill({ json: [] });
    });

    await page.goto("/app/customer/measurements");
    await page.getByRole("button", { name: "Add measurements" }).click();
    await expect(page.getByRole("heading", { name: "Measure with photos" })).toBeVisible();
    await page.getByLabel("Full-body photo").setInputFiles({ name: "me.jpg", mimeType: "image/jpeg", buffer: jpeg });
    await page.getByLabel("Tape-measure photos").setInputFiles({ name: "tape.jpg", mimeType: "image/jpeg", buffer: jpeg });
    await page.getByLabel("Your height (cm)").fill("172");
    await page.getByRole("button", { name: "Analyse photos" }).click();
    await expect(page.getByText("Read from tape · 92%")).toBeVisible();
    expect(analyzeCalls).toBe(1);
    await page.getByRole("region", { name: "Measure with photos" })
      .screenshot({ path: info.outputPath(`draft-${viewport.width}.png`) });

    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Use these in my form" }).click();
    await expect(page.getByText("Photo estimate, please confirm").first()).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({ path: info.outputPath(`measure-${viewport.width}.png`), fullPage: true });
  });
}

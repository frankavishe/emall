import { test, expect } from "@playwright/test";

// Staging smoke gate: confirms the deployed build serves the homepage and the
// guest nav can reach the product catalog. Expand with real user journeys as
// the E2E suite grows.
test("homepage loads and guest nav reaches the product catalog", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/E-Mall/);

  await page.getByRole("link", { name: "Products" }).click();
  await expect(page).toHaveURL(/\/products$/);
});

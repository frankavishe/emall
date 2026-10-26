import { test, expect } from "@playwright/test";

// Staging smoke gate: confirms the deployed build serves the homepage and the
// guest nav can reach the product catalog. Expand with real user journeys as
// the E2E suite grows.
test("homepage loads and guest nav reaches the product catalog", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/E-Mall/);

  await page.getByRole("link", { name: "Products", exact: true }).click();
  await expect(page).toHaveURL(/\/products$/);
});

test("unknown URLs return 404 with the branded not-found page", async ({ page }) => {
  const response = await page.goto("/this-page-does-not-exist");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Go home" })).toBeVisible();
});

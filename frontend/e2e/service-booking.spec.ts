import { test, expect, type Browser, type Page } from "@playwright/test";

/*
 * Service booking, request to completion (008-service-bookings, T082).
 *
 * Needs the running stack (backend + frontend + Postgres), so it is skipped unless the
 * E2E_BOOKING_* variables below are set. Seed beforehand:
 * - a verified customer, the vendor who owns a published service in an approved services shop
 *   open every day (and Lipa Namba configured, so it is offered for a visit a week away),
 * - an administrator who can manage finance,
 * - for the last step only, a CONFIRMED booking at that shop whose visit has already started
 *   (`E2E_BOOKING_STARTED_ID`): a fresh request can't start for at least
 *   BOOKING_MIN_NOTICE_HOURS, so completion can't be reached in one run.
 *
 *   PLAYWRIGHT_BASE_URL=http://localhost:3001 \
 *   E2E_BOOKING_SERVICE_ID=… E2E_BOOKING_CUSTOMER=email:password \
 *   E2E_BOOKING_VENDOR=email:password E2E_BOOKING_ADMIN=email:password \
 *   E2E_BOOKING_STARTED_ID=… npm run test:e2e -- service-booking
 */

const SERVICE_ID = process.env.E2E_BOOKING_SERVICE_ID;
const STARTED_ID = process.env.E2E_BOOKING_STARTED_ID;

function account(name: string): { email: string; password: string } | null {
  const value = process.env[`E2E_BOOKING_${name}`];
  if (!value) return null;
  const at = value.indexOf(":");
  return { email: value.slice(0, at), password: value.slice(at + 1) };
}

const customer = account("CUSTOMER");
const vendor = account("VENDOR");
const admin = account("ADMIN");

test.skip(
  !SERVICE_ID || !customer || !vendor || !admin,
  "Set E2E_BOOKING_SERVICE_ID, E2E_BOOKING_CUSTOMER, E2E_BOOKING_VENDOR and E2E_BOOKING_ADMIN",
);
test.describe.configure({ mode: "serial" });

async function signedIn(browser: Browser, who: { email: string; password: string }) {
  const page = await (await browser.newContext()).newPage();
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(who.email);
  await page.getByLabel("Password", { exact: true }).fill(who.password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/$/);
  return page;
}

/** A date a week ahead in the market's zone (+03:00), as the date input wants it. */
function weekAhead(): string {
  const market = new Date(Date.now() + 3 * 3600_000 + 7 * 86400_000);
  return market.toISOString().slice(0, 10);
}

async function bookingCard(page: Page, note: string) {
  await page.goto("/vendor/bookings");
  return page.getByRole("listitem").filter({ hasText: `Note: ${note}` });
}

test("customer requests, provider accepts, customer pays and an admin confirms", async ({
  browser,
}) => {
  const note = `e2e booking ${Date.now()}`;

  // Customer requests a time.
  const customerPage = await signedIn(browser, customer!);
  await customerPage.goto(`/services/${SERVICE_ID}`);
  await customerPage.getByLabel("Date").fill(weekAhead());
  await customerPage.locator("button[aria-pressed]").first().click();
  await customerPage.getByLabel("Contact phone").fill("+255712345678");
  await customerPage.getByLabel("Note for the provider (optional)").fill(note);
  await customerPage.getByRole("button", { name: "Request this time" }).click();
  await expect(customerPage).toHaveURL(/\/bookings\/\d+$/);
  const bookingId = customerPage.url().match(/\/bookings\/(\d+)$/)![1];
  await expect(customerPage.getByText("Requested").first()).toBeVisible();

  // Provider accepts.
  const vendorPage = await signedIn(browser, vendor!);
  const card = await bookingCard(vendorPage, note);
  await card.getByRole("button", { name: "Accept" }).click();
  await expect(card.getByText("Awaiting payment")).toBeVisible();

  // Customer pays with Lipa Namba (no gateway needed).
  await customerPage.reload();
  const payment = customerPage.getByRole("region", { name: "Payment" });
  await payment.getByLabel("Payment method").selectOption("lipa_namba");
  await payment.getByLabel("Transaction ID").fill(`E2E${Date.now()}`);
  await payment.getByRole("button", { name: /^Pay / }).click();
  await expect(customerPage.getByText("Payment in progress")).toBeVisible();

  // An administrator finds it on the statement and confirms.
  const adminPage = await signedIn(browser, admin!);
  await adminPage.goto(`/admin/bookings/${bookingId}`);
  await adminPage.getByRole("button", { name: "Confirm payment" }).click();
  await adminPage.getByRole("button", { name: "Yes, received" }).click();
  await expect(adminPage.getByText("Confirmed").first()).toBeVisible();

  await customerPage.reload();
  await expect(customerPage.getByText("Confirmed").first()).toBeVisible();
});

test("provider marks a started visit completed", async ({ browser }) => {
  test.skip(!STARTED_ID, "Set E2E_BOOKING_STARTED_ID to a confirmed, started booking");

  const vendorPage = await signedIn(browser, vendor!);
  await vendorPage.goto("/vendor/bookings");
  await vendorPage.getByRole("button", { name: "Mark completed" }).first().click();
  await expect(vendorPage.getByText("Completed").first()).toBeVisible();
});

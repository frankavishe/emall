# Quickstart: Role-Aware Homepage & Shared Navigation

## Prerequisites

- Backend running with migrations applied: `cd backend && python manage.py migrate` then
  `python manage.py runserver`.
- Frontend running: `cd frontend && npm run dev`.
- Test accounts for each role (create via existing register flows / Django admin / fixtures):
  - A Customer.
  - A Vendor with **no** shop yet.
  - A Vendor whose shop is **PENDING**.
  - A Vendor whose shop is **APPROVED**, with at least one order for their shop.
  - A Vendor whose shop is **REJECTED**.
  - An Administrator.
- At least one published product in an APPROVED shop's catalog (for guest/customer highlights),
  and at least one shop currently PENDING (for the admin count) plus at least one platform order
  (for admin recent orders).

## Scenario 1 — Guest homepage (User Story 1)

1. Open `/` in a private/incognito window (no session).
2. **Expect**: marketing view with product highlights (or an empty state if the catalog is empty)
   and visible Login/Register CTAs. No cart/orders/vendor/admin content anywhere on the page.
3. Confirm the nav bar shows only: Home, Products, Login, Register.

## Scenario 2 — Shared navigation across roles (User Story 2)

1. Log in as each of Customer, Vendor, Administrator in turn.
2. For each, visit at least two different pages (e.g. `/`, then `/products`) and confirm the nav
   bar is present on both and its links match research.md §5's table for that role, with no links
   belonging to a different role.

## Scenario 3 — Customer homepage (User Story 3)

1. Log in as the Customer.
2. Land on `/` (per the login-redirect change) and confirm featured/recent products are shown,
   with links to Cart and Orders, and no guest Login/Register CTAs.
3. Empty-cart / no-orders case: confirm the links are still present and clicking them works
   (empty cart/orders pages, no errors).

## Scenario 4 — Vendor homepage, all three shop states (User Story 4)

1. Log in as the no-shop Vendor. **Expect**: homepage prompts to request a shop, linking to
   `/account`, no broken/empty summary section.
2. Log in as the PENDING-shop Vendor. **Expect**: status shown as pending; no order/product-
   management content presented as if active.
3. Log in as the REJECTED-shop Vendor. **Expect**: status shown as rejected, with a link to
   `/account` (not a resubmission form on the homepage itself).
4. Log in as the APPROVED-shop Vendor with at least one order. **Expect**: status shown as
   approved, up to 5 recent orders for their shop listed, and a working link to manage products.
5. Repeat step 4 for a Vendor with an approved shop but zero orders. **Expect**: an explicit empty
   state in the orders section, not an error.

## Scenario 5 — Administrator homepage (User Story 5)

1. Ensure at least one shop is PENDING; log in as Administrator. **Expect**: homepage shows the
   correct pending-shop count and a working link to the shop-approvals page.
2. Approve/reject all pending shops (via the existing admin shops page) so the count is zero,
   reload `/`. **Expect**: count shows 0, not an error or missing section.
3. Confirm recent platform orders are listed (up to 5) with a working link to the order-oversight
   page.

## Scenario 6 — Login/register redirect (FR-014)

1. Log out. Log back in as any role. **Expect**: landing page after login is `/`, not `/account`.
2. Register a new Customer account. **Expect**: landing page after registration is `/`.

## Regression checks

- Directly navigate (typed URL) to a role-restricted page (e.g. `/admin/shops`) as a
  mismatched/logged-out role. **Expect**: existing server-side/client-redirect enforcement still
  applies unchanged — this feature must not have weakened it.
- `backend`: `pytest` passes, including the new `tests/core/test_pagination.py` covering
  `page_size` honored/capped/default-unchanged.

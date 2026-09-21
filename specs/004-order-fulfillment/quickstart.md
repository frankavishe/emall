# Quickstart: Validating Vendor Order Fulfillment

Manual validation guide, not implementation code. Run after `/speckit-implement` has built this
feature's tasks, to confirm it works end to end per the Constitution's "run for real" requirement.

## Prerequisites

- 001-accounts-auth, 002-product-catalog, and 003-cart-checkout already implemented and working
  (this feature extends `OrderItem`, created only via `place_order()`).
- PostgreSQL running (`docker compose up`, `emall-postgres` container, host port 5433).
- `backend/`: venv dependencies installed (no new dependencies, plan.md Technical Context).
- `frontend/`: `npm install` up to date.
- Seed data: two Customer accounts, two Vendor accounts each with an APPROVED shop and at least one
  published product (ideally one Order that spans both vendors' shops — reuse
  003-cart-checkout's Scenario 2 multi-vendor checkout flow to produce it), and one Administrator
  account.

## Setup

```powershell
# From backend/
python manage.py migrate
python manage.py runserver
```

```powershell
# From frontend/, in a separate terminal
npm run dev
```

## Scenario 1 — Vendor views and fulfills their own order lines (User Story 1 / P1)

1. As Vendor A, place a test order as a Customer containing one of Vendor A's products (reuse
   003-cart-checkout's checkout flow), then log in as Vendor A.
2. `GET /api/vendor/order-items/`.
   - **Expect**: `200`, the just-placed line appears with `status: "PENDING"`, product, quantity,
     and shipping details — enough to fulfill it without a second lookup.
3. `PATCH /api/vendor/order-items/{id}/status/` with `{ "status": "PROCESSING" }`.
   - **Expect**: `200`, `status: "PROCESSING"`; re-`GET` the list and confirm it persists.
4. `PATCH .../status/` with `{ "status": "SHIPPED" }`, then again with `{ "status": "DELIVERED" }`.
   - **Expect**: each `200`, status advances one step at a time.
5. Build a second cart as a different Customer with products from both Vendor A's and Vendor B's
   shops, check out, then have Vendor A advance their own line.
   - **Expect**: Vendor B's line on the same order is unaffected; `GET /api/vendor/order-items/` as
     Vendor B never shows Vendor A's line, and `PATCH` on Vendor A's line ID as Vendor B returns
     `404`.

## Scenario 2 — Customer sees fulfillment progress (User Story 2 / P1)

1. As the Customer who placed Scenario 1's order, `GET /api/orders/{id}/`.
   - **Expect**: the line shows `status: "DELIVERED"` (or whatever Scenario 1 left it at).
2. In the browser: visit `/orders/{id}` and confirm the same status renders on the existing order
   detail page (no new page needed — verifying research.md §7's "no new work" finding).
3. Place a fresh order, advance its line one step as the Vendor, then reload the Customer's
   `/orders/{id}` page.
   - **Expect**: the new status appears after the reload, no other field changed.

## Scenario 3 — Invalid transitions are rejected (Edge Cases / SC-002)

1. With a line at `PENDING`, `PATCH .../status/` with `{ "status": "DELIVERED" }` (skipping steps).
   - **Expect**: `400`, status remains `PENDING`.
2. With a line at `PROCESSING`, `PATCH .../status/` with `{ "status": "PENDING" }` (backward).
   - **Expect**: `400`, status remains `PROCESSING`.
3. With a line at `DELIVERED`, `PATCH .../status/` with any status.
   - **Expect**: `400`, status remains `DELIVERED`.
4. With a line at `SHIPPED`, `PATCH .../status/` with `{ "status": "CANCELLED" }`.
   - **Expect**: `400` — cancellation isn't reachable once shipped (spec Assumptions).

## Scenario 4 — Cancellation restores stock (FR-011 / SC-006)

1. Note a product's current `stock_quantity` via `GET /api/catalog/products/{id}/`. Place an order
   for `quantity: 2` of it, then as the owning Vendor `PATCH .../status/` with
   `{ "status": "CANCELLED" }` on that line (from `PENDING` or `PROCESSING`).
   - **Expect**: `200`, line `status: "CANCELLED"`; re-`GET` the product and confirm
     `stock_quantity` increased by exactly `2` from the noted value.
2. Attempt to advance the now-`CANCELLED` line further.
   - **Expect**: `400` — terminal state, no further stock change.

## Scenario 5 — Administrator oversight (User Story 3 / P3)

1. As the Administrator, `GET /api/admin/order-items/`.
   - **Expect**: `200`, line items from both Vendor A's and Vendor B's shops appear, each showing
     its current status, its shop/vendor identity, and a `status_history` array with one entry per
     transition made in Scenarios 1–4.
2. Confirm no endpoint under `/api/admin/order-items/` accepts a `PATCH`/`POST`/`DELETE` (oversight
   is read-only, FR-008).
3. As Vendor A (not Administrator), `GET /api/vendor/order-items/` for a line with history.
   - **Expect**: the response includes `status` but no `status_history` field (Administrator-only
     visibility, Clarifications session 2026-09-21).

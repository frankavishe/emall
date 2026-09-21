# Quickstart: Validating Order Status Notifications

Manual validation guide, not implementation code. Run after `/speckit-implement` has built this
feature's tasks, to confirm it works end to end per the Constitution's "run for real" requirement.

## Prerequisites

- 001-accounts-auth, 003-cart-checkout, and 004-order-fulfillment already implemented and working
  (this feature reacts to `advance_order_item_status()`, which 004 introduced).
- PostgreSQL running (`docker compose up`, `emall-postgres` container, host port 5433).
- `backend/`: venv dependencies installed (no new dependencies, plan.md Technical Context).
- Local dev `EMAIL_BACKEND` set to Django's console backend (prints emails to the `runserver`
  terminal instead of attempting real SMTP) — matches how 001-accounts-auth's verification/reset
  emails are already validated locally; no new configuration for this feature.
- Seed data: one Customer account, one Vendor account with an APPROVED shop and at least one
  published product, and one placed Order containing that product (reuse 003-cart-checkout's
  checkout flow to produce it).

## Setup

```powershell
# From backend/
python manage.py migrate
python manage.py runserver
```

## Scenario 1 — Customer is emailed when their item ships and is delivered (User Story 1 / P1)

1. As the Vendor, `PATCH /api/vendor/order-items/{id}/status/` with `{ "status": "PROCESSING" }`
   on the seeded order line (moving it off `PENDING` first, per the existing transition rules).
   - **Expect**: `200`; the `runserver` console prints an email addressed to the Customer's
     account email, subject "Your order is being prepared", naming the order and the product.
2. `PATCH .../status/` with `{ "status": "SHIPPED" }`.
   - **Expect**: `200`; a second, separate console email appears, subject "Your order has
     shipped", naming the same order/product.
3. `PATCH .../status/` with `{ "status": "DELIVERED" }`.
   - **Expect**: `200`; a third console email appears, subject "Your order has been delivered".
   - Confirm exactly one email printed per `PATCH` call — three calls, three emails, not one
     combined summary (FR-004, SC-001).

## Scenario 2 — Customer is emailed when their item is cancelled (User Story 2 / P2)

1. Seed a second order line still in `PENDING` (or `PROCESSING`).
2. As its Vendor, `PATCH .../status/` with `{ "status": "CANCELLED" }`.
   - **Expect**: `200`; a console email appears, subject "An item in your order was cancelled",
     naming the order/product, and containing no mention of a refund or payment outcome (FR-008 —
     read the full body text to confirm).

## Scenario 3 — Customer is emailed when their item enters processing (User Story 3 / P3)

Covered by Scenario 1 step 1 above (`PENDING` → `PROCESSING`) — no separate setup needed.

## Scenario 4 — No notification on a rejected transition (SC-002)

1. Take an order line already `DELIVERED` (from Scenario 1) or `CANCELLED` (from Scenario 2).
2. `PATCH .../status/` with any `{ "status": ... }` value.
   - **Expect**: `400` (invalid transition, per 004-order-fulfillment's existing contract); no new
     email appears in the console output.

## Scenario 5 — Unverified Customer email still receives notifications (FR-006)

1. Seed a Customer whose `is_email_verified` is `false` (e.g. skip the verify-email step from
   001-accounts-auth), with an order line belonging to them.
2. As the Vendor, advance that line's status.
   - **Expect**: the console email still appears, addressed to that Customer — verification status
     has no bearing on this feature.

## Scenario 6 — Notification failure does not block the status change (FR-005, SC-004)

This is exercised by an automated test (per plan.md Testing), not manually: a test forces the
email service to raise on send and asserts the `PATCH` still returns `200` with the status
persisted in the database, and that the error was logged rather than propagated. No manual browser
step is needed for this scenario.

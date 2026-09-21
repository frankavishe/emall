# Quickstart: Validating Shopping Cart & Checkout

Manual validation guide, not implementation code. Run after `/speckit-implement` has built this
feature's tasks, to confirm it works end to end per the Constitution's "run for real" requirement.

## Prerequisites

- 001-accounts-auth and 002-product-catalog already implemented and working (this feature depends
  on both: Customer login, and published products from APPROVED shops to add to a cart).
- PostgreSQL running (`docker compose up`, `emall-postgres` container, host port 5433).
- `backend/`: venv dependencies installed (no new dependencies, research.md §5).
- `frontend/`: `npm install` up to date.
- Seed data: at least one Customer account; two published products from at least one APPROVED
  shop, ideally spanning two different vendors' shops (reuse the catalog quickstart's Scenario 1
  flow to get products published).

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

## Scenario 1 — Customer builds and manages a persistent cart (User Story 1 / P1)

1. Log in as the Customer.
2. `POST /api/cart/items/` with `product_id` of Product A, `quantity: 2`.
   - **Expect**: `201`, line with `quantity: 2` and correct `subtotal`.
3. `POST /api/cart/items/` again with the same `product_id`, `quantity: 1`.
   - **Expect**: `200` (merged, not a new line), that line now shows `quantity: 3`.
4. Log out, log back in (or hit `GET /api/cart/` fresh from a different client/session).
   - **Expect**: the same cart contents are returned.
5. `PATCH /api/cart/items/{id}/` changing `quantity` to `5`.
   - **Expect**: `200`, line and cart total updated.
6. Add a second product (Product B) to the cart, then `DELETE /api/cart/items/{id}/` for Product
   A's line.
   - **Expect**: `204`; `GET /api/cart/` now shows only Product B, correct total.
7. `POST /api/cart/items/` requesting a `quantity` greater than Product B's `stock_quantity`.
   - **Expect**: `400`, message states the maximum available quantity, no line created/changed.
8. In the browser: visit `/products`, add an item to the cart via the UI, then visit `/cart` and
   repeat the quantity-change and remove steps through the UI.

## Scenario 2 — Customer completes checkout (User Story 2 / P1)

1. With a non-empty cart containing products from a single vendor's shop, `POST /api/checkout/`
   with valid shipping details and `payment_method: "card"`.
   - **Expect**: `201`, an `Order` with one `OrderItem` per cart line (correct product/quantity/
     price), the cart is now empty (`GET /api/cart/` → `items: []`), and each ordered product's
     `stock_quantity` decreased by the ordered amount (verify via `GET /api/catalog/products/{id}/`
     or the vendor product endpoint).
2. Build a new cart with products from two different vendors' shops, then check out.
   - **Expect**: `201`, a single `Order` whose `items` span both shops, each item carrying its own
     `status` independently.
3. With an empty cart, `POST /api/checkout/`.
   - **Expect**: `400`, clear "cart is empty" message, no `Order` created.
4. Add a product to the cart, then (as the owning Vendor, in another session) reduce that
   product's `stock_quantity` below the cart's requested quantity, then attempt checkout.
   - **Expect**: `400`, names the specific line as the problem, no `Order` created, no stock
     changed.
5. Add a product to the cart and check out with `payment_method: "declined"` (research.md §5
   sentinel).
   - **Expect**: `400` payment-declined error, no `Order` created, no stock decremented, and
     `GET /api/cart/` shows the cart unchanged (still has the item).
6. Check out with a shipping payload missing `postal_code`.
   - **Expect**: `400`, field-level error naming `postal_code`, no `Order` created.
7. In the browser: visit `/checkout` with a non-empty cart, fill the shipping form, confirm, and
   land on the order confirmation.

## Scenario 3 — Cart reflects live catalog changes (User Story 3 / P2)

1. Add a product to the cart. As the owning Vendor, change that product's `price` via the catalog
   API. `GET /api/cart/` as the Customer.
   - **Expect**: the line shows the new price and recalculated subtotal, not the price at add-time.
2. As the owning Vendor, unpublish that product. `GET /api/cart/` as the Customer.
   - **Expect**: the line is present but flagged `is_available: false`, excluded from `total`.
3. Attempt `POST /api/checkout/` with that line still in the cart.
   - **Expect**: `400`, blocked until the Customer removes or adjusts that line (per Scenario 2
     step 4's shape).
4. In the browser: with the cart page open, have the vendor unpublish the product in another tab,
   refresh `/cart`, and confirm the unavailable flag renders and checkout is disabled/blocked.

## Scenario 4 — Customer reviews past orders (User Story 4 / P3)

1. As the Customer from Scenario 2, `GET /api/orders/`.
   - **Expect**: `200`, both placed orders listed, most recent first, each with date/total/status.
2. `GET /api/orders/{id}/` for one of them.
   - **Expect**: full detail — every line item, shipping details, per-line status.
3. Log in as a *different* Customer and `GET /api/orders/{id}/` using the first Customer's order
   ID.
   - **Expect**: `404` (research.md §6) — not `403`, not the order's data.
4. In the browser: visit `/orders`, confirm both orders render, open one and confirm `/orders/
   [id]` shows full detail.

## Scenario 5 — Validation and edge cases

1. `POST /api/cart/items/` with `quantity: 0`.
   - **Expect**: `400`.
2. `POST /api/cart/items/` for a product from a shop that is not (or no longer) APPROVED.
   - **Expect**: `400`, not addable.
3. Simulate the concurrent-oversell race: with a product at `stock_quantity: 1`, have two
   Customers each add `quantity: 1` to their separate carts, then fire both checkouts
   back-to-back. — **Expect**: exactly one `201`, the other `400` with a stock-conflict message
   naming the line, and the product's final `stock_quantity` is `0`, never negative (research.md
   §4). This is best exercised as an automated test (two threads/connections hitting
   `place_order()` around the same `select_for_update()`-protected row) rather than manually timed
   requests.

# Quickstart: Validating Product Catalog

Manual validation guide, not implementation code. Run after `/speckit-implement` has built this
feature's tasks, to confirm it works end to end per the Constitution's "run for real" requirement.

## Prerequisites

- 001-accounts-auth already implemented and working (this feature depends on it for Vendor login
  and an APPROVED shop to list products under).
- PostgreSQL running (`docker compose up`, `emall-postgres` container, host port 5433).
- `backend/`: venv dependencies installed, including the new `Pillow` dependency (research.md §1).
- `frontend/`: `npm install` up to date.
- Seed data: at least one Vendor account with one APPROVED shop, and one with a still-PENDING shop
  (reuse the accounts-auth quickstart's Scenario 2/3 flow, or the `seed_admin` command plus a
  manual admin-approve call, to get here).

## Setup

```powershell
# From backend/
python manage.py migrate      # includes the Category seed data migration (research.md §3)
python manage.py runserver
```

```powershell
# From frontend/, in a separate terminal
npm run dev
```

## Scenario 1 — Vendor creates, edits, publishes, unpublishes a product (User Story 1 / P1)

1. Log in as the Vendor with the APPROVED shop.
2. `POST /api/vendor/products/` with `shop_id` set to the APPROVED shop, valid name/description/
   price/stock/category, no images.
   - **Expect**: `201`, `is_published: false`.
3. `GET /api/catalog/products/` (unauthenticated).
   - **Expect**: the new product does NOT appear (still a draft).
4. `PATCH /api/vendor/products/{id}/` changing `price`.
   - **Expect**: `200`, price updated.
5. `POST /api/vendor/products/{id}/publish/`.
   - **Expect**: `200`, `is_published: true`.
6. Re-run `GET /api/catalog/products/` (unauthenticated).
   - **Expect**: the product now appears.
7. `POST /api/vendor/products/{id}/unpublish/`.
   - **Expect**: `200`, `is_published: false`; re-run step 6's request and confirm it's gone again,
     but `GET /api/vendor/products/{id}/`-equivalent (or the list) still shows it to the Vendor.
8. In the browser: visit `/vendor/products`, repeat create → publish → unpublish through the UI.

## Scenario 2 — Approval gate blocks a non-approved shop (User Story 2 / P1)

1. Log in as the Vendor with the still-PENDING shop (or reuse the second shop from Scenario 2 in
   the accounts-auth quickstart).
2. `POST /api/vendor/products/` with `shop_id` set to the PENDING shop, valid fields otherwise.
   - **Expect**: `403`, clear "shop not approved" message, no product created. Do this via a direct
     API call (curl/Postman), not just the UI, to confirm the server enforces it independent of any
     client-side check (SC-002).
3. If that Vendor also owns an APPROVED shop, repeat step 2 with the APPROVED shop's `shop_id`.
   - **Expect**: `201` succeeds, proving the gate is per-shop not per-account.

## Scenario 3 — Customer browses, searches, filters (User Story 3 / P2)

1. As an unauthenticated visitor, `GET /api/catalog/products/`.
   - **Expect**: only published products from APPROVED shops.
2. `GET /api/catalog/products/?q=<keyword from a published product's name>`.
   - **Expect**: that product is returned; unrelated products are not.
3. `GET /api/catalog/products/?category=<seeded category slug>&min_price=1&max_price=1000`.
   - **Expect**: only matching published products within the price range and category.
4. `GET /api/catalog/products/?q=zzzznonexistentzzzz`.
   - **Expect**: `200` with `"results": []`, not an error (Edge Cases).
5. `GET /api/catalog/products/{id}/` for a published product.
   - **Expect**: full detail including `stock_status` and `shop.name`.
6. In the browser: visit `/products`, use the search box and category/price filters, then open a
   product's detail page.

## Scenario 4 — Out-of-stock display (Edge Case / FR-011)

1. As the owning Vendor, `PATCH` a published product's `stock_quantity` to `0`.
2. `GET /api/catalog/products/{id}/` (unauthenticated).
   - **Expect**: `200`, `stock_status: "out_of_stock"`, product still visible (not hidden).
3. `GET /api/catalog/products/` and confirm the same product still appears in listing results with
   `in_stock: false`.

## Scenario 5 — Validation rejects bad input (FR-012, FR-013)

1. `POST /api/vendor/products/` with a negative `price`.
   - **Expect**: `400`.
2. `POST /api/vendor/products/` with a negative `stock_quantity`.
   - **Expect**: `400`.
3. `POST /api/vendor/products/` twice with the same `name` under the same `shop_id`.
   - **Expect**: second call `400`, duplicate name.
4. `POST /api/vendor/products/` with that same `name` but a *different* `shop_id` the Vendor also
   owns.
   - **Expect**: `201` succeeds — name uniqueness is per-shop, not global (Edge Cases).

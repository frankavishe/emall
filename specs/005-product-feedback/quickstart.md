# Quickstart: Validating Product Feedback & Reviews

Manual validation guide, not implementation code. Run after `/speckit-implement` has built this
feature's tasks, to confirm it works end to end per the Constitution's "run for real" requirement.

## Prerequisites

- 001-accounts-auth, 002-product-catalog, 003-cart-checkout, and 004-order-fulfillment already
  implemented and working (this feature gates on `OrderItem.status == DELIVERED`).
- PostgreSQL running (`docker compose up`, `emall-postgres` container, host port 5433).
- `backend/`: venv dependencies installed (no new dependencies, plan.md Technical Context).
- `frontend/`: `npm install` up to date.
- Seed data: two Customer accounts (Customer A, Customer B), two Vendor accounts each with an
  APPROVED shop and at least one published product, and one Administrator account. At least one
  Order/OrderItem for Customer A on Vendor A's product advanced all the way to `DELIVERED`
  (reuse 004-order-fulfillment's Scenario 1/4 flow: place order as Customer A, advance the line as
  Vendor A through PROCESSING → SHIPPED → DELIVERED).

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

## Scenario 1 — Customer leaves a review on a delivered product (User Story 1 / P1)

1. As Customer A (whose `OrderItem` for Vendor A's product is `DELIVERED`),
   `POST /api/feedback/products/{product_id}/review/` with `{ "rating": 5, "comment": "Great!" }`.
   - **Expect**: `201`, the review is returned with the submitted rating/comment.
2. Submit again with `{ "rating": 4, "comment": "Updating my review." }` for the same product.
   - **Expect**: `200` (not `201`), the same review `id` as step 1, now showing `rating: 4`.
3. Submit with `{ "rating": 3 }` (no `comment`).
   - **Expect**: `200`, `comment: ""` — rating alone is sufficient.
4. As Customer B, who has never had an `OrderItem` for this product,
   `POST /api/feedback/products/{product_id}/review/` with `{ "rating": 5 }`.
   - **Expect**: `403` — no DELIVERED purchase (FR-002).

## Scenario 2 — Shoppers see reviews and aggregate rating (User Story 2 / P1)

1. Without logging in, `GET /api/catalog/products/{product_id}/`.
   - **Expect**: `200`, response includes `reviews` (Customer A's current review), `average_rating`,
     and `review_count: 1`.
2. In the browser: visit `/products/{product_id}` and confirm the rating/comment render on the
   page without logging in.
3. `GET /api/catalog/products/{other_product_id}/` for a product with no reviews.
   - **Expect**: `average_rating: null`, `review_count: 0`, `reviews: []` — no error.

## Scenario 3 — Vendor views feedback on their own shop (User Story 3 / P2)

1. As Vendor A, `GET /api/vendor/reviews/`.
   - **Expect**: `200`, Customer A's review on Vendor A's product appears, with the product it
     belongs to.
2. As Vendor B (a different shop, no reviews on their products yet), `GET /api/vendor/reviews/`.
   - **Expect**: `200`, empty results — Vendor A's review never appears here (FR-009).
3. Confirm no `PATCH`/`DELETE` endpoint exists under `/api/vendor/reviews/` (read-only, FR-008).

## Scenario 4 — Administrator moderates a review (User Story 4 / P3)

1. As the Administrator, `GET /api/admin/reviews/`.
   - **Expect**: `200`, Customer A's review appears with product, shop, and customer identity.
2. `DELETE /api/admin/reviews/{review_id}/`.
   - **Expect**: `204`.
3. Re-run Scenario 2 step 1 (`GET /api/catalog/products/{product_id}/`).
   - **Expect**: `review_count: 0`, `average_rating: null`, the removed review absent from
     `reviews`.
4. As Customer A, `GET /api/feedback/products/{product_id}/review/` equivalent check — attempt to
   submit a fresh review via `POST .../review/` with `{ "rating": 4 }`.
   - **Expect**: `201` (treated as a brand-new review, not a restoration of the removed one, since
     Customer A still has a DELIVERED `OrderItem`).

## Scenario 5 — One review per customer per product, and self-service edit/delete (SC-006, FR-004)

1. As Customer A, `DELETE /api/feedback/products/{product_id}/review/` (their own review from
   Scenario 4 step 4).
   - **Expect**: `204`.
2. Repeat the same `DELETE`.
   - **Expect**: `404` — nothing left to delete.
3. Confirm at no point in Scenarios 1–5 did more than one row exist for the (Customer A, this
   product) pair — every repeat `POST` updated the same review `id`.

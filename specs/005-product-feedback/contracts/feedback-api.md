# API Contract: Product Feedback & Reviews

Base paths: `/api/catalog/` (public read, extended), `/api/feedback/` (Customer write),
`/api/vendor/reviews/` (Vendor read), `/api/admin/reviews/` (Administrator read + moderate). All
bodies JSON. Traceability: each endpoint references the FR(s) it satisfies.

## Public product read (extends existing `002-product-catalog` endpoints — no new path)

`GET /api/catalog/products/` and `GET /api/catalog/products/{id}/` (`AllowAny`, unchanged
permissions) gain two extra response fields, satisfying FR-005/FR-006:

```json
{
  "id": 5, "name": "USB-C Cable", "...": "...existing fields unchanged...",
  "average_rating": 4.5,
  "review_count": 2,
  "reviews": [
    { "id": 9, "customer_display_name": "Ama O.", "rating": 5,
      "comment": "Works great, fast shipping.", "created_at": "2026-09-20T08:00:00Z" },
    { "id": 11, "customer_display_name": "Kwesi A.", "rating": 4, "comment": "",
      "created_at": "2026-09-21T14:00:00Z" }
  ]
}
```

`reviews` is included only on the detail endpoint (`CatalogProductDetailSerializer`), matching
where a shopper reads them (spec User Story 2); the list endpoint
(`CatalogProductListSerializer`) exposes only `average_rating`/`review_count` for the browse grid.
A product with no reviews returns `"average_rating": null, "review_count": 0, "reviews": []`
(User Story 2, Scenario 2). No `Authorization` required — visible to logged-out shoppers.

## Customer review submission (`/api/feedback/`)

Requires `Authorization: Bearer <access_token>` and `role == CUSTOMER`
(`apps.core.permissions.IsCustomer`).

### `POST /api/feedback/products/{product_id}/review/`
Satisfies FR-001, FR-002, FR-003, FR-004 (create-or-update upsert, research.md §3). Request:
```json
{ "rating": 5, "comment": "Works great, fast shipping." }
```
(`comment` optional.)

Response `201` (first submission) or `200` (update to an existing review) — the saved review:
```json
{ "id": 9, "product_id": 5, "rating": 5, "comment": "Works great, fast shipping.",
  "created_at": "2026-09-20T08:00:00Z", "updated_at": "2026-09-20T08:00:00Z" }
```

Errors:
- `400` `{ "rating": ["Must be between 1 and 5."] }` — invalid/missing rating.
- `403` `{ "detail": "You can only review products you have received." }` — no `OrderItem` with
  `status=DELIVERED` for this (customer, product) pair (FR-002; research.md §2).

### `DELETE /api/feedback/products/{product_id}/review/`
Satisfies FR-004 (Customer deletes their own review). Only the owning Customer may call this for
their own review; no other Customer's review is reachable through this path (the URL is scoped by
`product_id`, resolved to `request.user`'s own review server-side, never a review `id` another
customer could guess).

Response `204`. Error `404` if the requester has no review on this product.

## Vendor feedback view (`/api/vendor/reviews/`)

Requires `Authorization: Bearer <access_token>` and `role == VENDOR`
(`apps.core.permissions.IsVendor`). Read-only — no mutating endpoint here (FR-008).

### `GET /api/vendor/reviews/`
Satisfies FR-007, FR-009. Lists reviews on products belonging to one of the authenticated Vendor's
own shops, across all their products, paginated, queryset-filtered
(`Review.objects.filter(product__shop__owner=request.user)` — research.md §5).

Response `200`:
```json
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 9, "product": { "id": 5, "name": "USB-C Cable" },
      "customer_display_name": "Ama O.", "rating": 5,
      "comment": "Works great, fast shipping.", "created_at": "2026-09-20T08:00:00Z" }
  ]
}
```
No review belonging to another vendor's shop ever appears (FR-009).

## Administrator moderation (`/api/admin/reviews/`)

Requires `Authorization: Bearer <access_token>` and `role == ADMINISTRATOR`
(`apps.core.permissions.IsAdministrator`).

### `GET /api/admin/reviews/`
Satisfies FR-010. Lists every review across all products/shops, paginated, including which
product/shop each belongs to and the reviewing customer.

Response `200`:
```json
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 9, "product": { "id": 5, "name": "USB-C Cable" },
      "shop": { "id": 3, "name": "Kofi's Electronics" },
      "customer": { "id": 21, "email": "ama@example.com" },
      "rating": 5, "comment": "Works great, fast shipping.",
      "created_at": "2026-09-20T08:00:00Z" }
  ]
}
```

### `DELETE /api/admin/reviews/{review_id}/`
Satisfies FR-011, FR-012. Removes the review (hard delete, research.md §6). After removal it is
absent from the public product page, the Vendor feedback view, and `average_rating`/`review_count`
(recomputed on next read, since those are derived — data-model.md).

Response `204`. Error `404` if the review doesn't exist (already removed, or never existed).

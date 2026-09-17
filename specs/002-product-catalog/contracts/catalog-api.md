# API Contract: Product Catalog

Base paths: `/api/vendor/products/` (vendor management, auth required) and `/api/catalog/`
(public browse/search/detail, no auth required). All bodies JSON except image upload
(`multipart/form-data`). Traceability: each endpoint references the FR(s) it satisfies.

## Vendor product management (`/api/vendor/products/`)

All endpoints require `Authorization: Bearer <access_token>` and `role == VENDOR`. Every
create/update/delete/publish action is additionally scoped through `IsApprovedShopOwnerForProduct`
(data-model.md, research.md §5) — a Vendor can only act on products whose `shop.owner == request
.user`, and create/publish additionally require `shop.status == APPROVED`.

### `GET /api/vendor/products/`
Satisfies FR-006. Lists only products belonging to shops the authenticated Vendor owns, across all
their shops, paginated (research.md §6). Query param `shop_id` optionally narrows to one shop.

Response `200`:
```json
{
  "count": 3, "next": null, "previous": null,
  "results": [
    { "id": 1, "shop": { "id": 5, "name": "Kofi's Electronics" }, "name": "USB-C Cable",
      "price": "9.99", "stock_quantity": 40, "category": "electronics",
      "is_published": true, "images": [ { "id": 1, "url": "/media/products/1/a.jpg" } ] }
  ]
}
```

### `POST /api/vendor/products/`
Satisfies FR-001, FR-002, FR-012, FR-013. `multipart/form-data` to allow image files alongside
fields.

Request fields: `shop_id`, `name`, `description`, `price`, `stock_quantity`, `category` (slug),
`images[]` (optional, 0+ files).

Response `201`: same shape as a list item, `is_published: false`.
Errors: `403` shop not APPROVED or not owned by requester (FR-002); `400` negative price/stock
(FR-012), duplicate name within that shop (FR-013), missing required field.

### `PATCH /api/vendor/products/{id}/`
Satisfies FR-003. Partial update of any field (name, description, price, stock_quantity,
category, add/remove images). Allowed regardless of `is_published` state.

Response `200`: updated product. Errors: `403` not the owning Vendor; `400` validation failure
(FR-012/FR-013 same as create).

### `POST /api/vendor/products/{id}/publish/`
Satisfies FR-004. No body. Requires `shop.status == APPROVED` (re-checked at publish time, not
just at creation time, since a shop could theoretically change status between creation and
publish) and all required fields present.

Response `200`: `{ "id": 1, "is_published": true }`.
Errors: `403` shop not approved / not owner; `400` `{ "missing_fields": ["price", "category"] }`
when a required field is absent (Edge Cases).

### `POST /api/vendor/products/{id}/unpublish/`
Satisfies FR-005. No body.

Response `200`: `{ "id": 1, "is_published": false }`. Errors: `403` not owner.

### `DELETE /api/vendor/products/{id}/`
Satisfies FR-014. Soft delete (data-model.md) — sets `is_deleted=True`, `deleted_at=now()`.

Response `204`. Errors: `403` not owner.

## Public catalog (`/api/catalog/`)

No authentication required. Every response is restricted server-side to `is_published=True AND
is_deleted=False AND shop.status=APPROVED` (data-model.md "Visibility"), regardless of any
client-supplied filter.

### `GET /api/catalog/products/`
Satisfies FR-007, FR-008, FR-009, FR-011. Paginated (`PAGE_SIZE=20`).

Query params (all optional, combinable — research.md §2):
- `q` — keyword, matched against `name` and `description` (`icontains`, OR'd)
- `category` — category slug, exact match
- `min_price`, `max_price` — inclusive price range

Response `200`:
```json
{
  "count": 12, "next": "...", "previous": null,
  "results": [
    { "id": 1, "name": "USB-C Cable", "price": "9.99", "category": "electronics",
      "in_stock": true, "shop_name": "Kofi's Electronics",
      "thumbnail_url": "/media/products/1/a.jpg" }
  ]
}
```
`in_stock` is a derived boolean (`stock_quantity > 0`), never the raw count, per FR-011's "in
stock / out of stock, not necessarily the exact count."

An empty `results` array (with `count: 0`) is a normal `200`, not an error (Edge Cases).

### `GET /api/catalog/products/{id}/`
Satisfies FR-010, FR-011. `404` if the product doesn't exist, isn't published, is soft-deleted, or
its shop isn't APPROVED — the same "not found" response in all four cases, so unauthenticated
enumeration can't distinguish "never existed" from "exists but hidden."

Response `200`:
```json
{
  "id": 1, "name": "USB-C Cable", "description": "1m braided cable",
  "price": "9.99", "category": { "name": "Electronics", "slug": "electronics" },
  "stock_status": "in_stock",
  "shop": { "id": 5, "name": "Kofi's Electronics" },
  "images": [ { "id": 1, "url": "/media/products/1/a.jpg", "position": 0 } ]
}
```
`stock_status` is `"in_stock"` or `"out_of_stock"` (FR-011).

### `GET /api/catalog/categories/`
Not required by any FR directly, but needed for the frontend filter UI to populate the category
dropdown without hardcoding the seeded list. Read-only, no auth.

Response `200`: `[ { "name": "Electronics", "slug": "electronics" }, ... ]`.

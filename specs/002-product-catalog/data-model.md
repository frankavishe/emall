# Phase 1 Data Model: Product Catalog

Source: `spec.md` Key Entities, Functional Requirements FR-001–FR-015. All fields live in
PostgreSQL (Constitution Principle IV: schema is "real core", never mocked).

## Category (`apps/catalog/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `name` | `CharField`, unique | Global, admin-owned per spec Assumptions — this feature only reads/seeds it, no CRUD endpoint |
| `slug` | `SlugField`, unique | Used in filter query params (`?category=electronics`) so URLs stay stable if `name` display text changes |

**Validation rules**: Seeded via data migration (research.md §3), not user-creatable in this
feature.

**Relationships**: One `Category` → many `Product`.

## Product (`apps/catalog/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `shop` | `ForeignKey(Shop, related_name="products")`, `on_delete=CASCADE` | Ownership anchor — every authorization check (FR-002, FR-006) resolves through this FK, per research.md §5 |
| `category` | `ForeignKey(Category, related_name="products")`, `on_delete=PROTECT`, `null=True` | `PROTECT` so a category can never be deleted out from under existing products; **nullable** — see "Draft-required fields" below |
| `name` | `CharField` | Uniqueness enforced per-shop, not globally — FR-013. The only field required at creation time — a draft needs at least a name to exist as a row |
| `description` | `TextField(blank=True, default="")` | Nullable-in-spirit via empty string (not `null=True` — string fields use `""`, standard Django convention); see "Draft-required fields" |
| `price` | `DecimalField(max_digits=10, decimal_places=2, null=True)` | `Decimal`, not float, to avoid rounding drift on money — validated `>= 0` when present (FR-012); nullable, see below |
| `stock_quantity` | `PositiveIntegerField(null=True)` | DB-level non-negative constraint satisfies FR-012 for stock directly; also the decrementable counter FR-015 requires for a future checkout feature; nullable so "missing" (`None`) is distinguishable from "explicitly zero" (a valid, published, out-of-stock product — FR-011) |
| `is_published` | `BooleanField`, default `False` | Draft vs. published (FR-001, FR-004, FR-005) |
| `is_deleted` | `BooleanField`, default `False` | Soft delete — research.md §4 |
| `deleted_at` | `DateTimeField`, nullable | Set when `is_deleted` flips `True` |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `updated_at` | `DateTimeField(auto_now=True)` | |

**Validation rules**:
- `(shop_id, name)` unique together — FR-013.
- `price >= 0`, `stock_quantity >= 0` — FR-012 (DB `CheckConstraint` for `price`, allowing `NULL`;
  `stock_quantity` is non-negative by field type already, independent of nullability).
- **Draft-required fields**: only `name` (plus `shop`) is required to create a `Product` row at
  all — this is what makes an incomplete draft representable (spec Edge Cases: "saving as an
  unpublished draft with incomplete fields is still allowed"). `description`, `price`,
  `stock_quantity`, `category` may be absent on a draft.
- Publish action (`is_published: False → True`) only allowed when `description` (non-empty),
  `price`, `stock_quantity`, and `category` are all present/non-null — FR-004. Enforced at the
  serializer/view layer via `Product.missing_fields_for_publish()`, not as a DB constraint.
- Create/publish only permitted when `shop.status == APPROVED` — FR-002, enforced by
  `IsApprovedShopOwnerForProduct` (research.md §5), never by the client.
- Soft-deleted products (`is_deleted=True`) are excluded from every default queryset (custom
  manager) so no code path needs to remember to filter them — FR-014.

**State machine** (`is_published` × `is_deleted`, `is_deleted` is a one-way terminal flag):

```
        (Vendor creates product)
                    │
                    ▼
            DRAFT (is_published=False)
              │                  ▲
   (Vendor publishes,   (Vendor unpublishes)
    all fields valid)            │
              ▼                  │
          PUBLISHED (is_published=True) ──┐
              │                            │
              └──────────(Vendor deletes, from either state)
                                    ▼
                          DELETED (is_deleted=True, terminal)
```

Visibility to Customers = `is_published=True AND is_deleted=False AND shop.status=APPROVED`
(spec Assumptions) — computed at query time, not cached as a denormalized flag, so a shop's
approval status change takes effect on products immediately with no cascade step required.

**Relationships**: One `Shop` (from 001-accounts-auth, referenced not redefined) → many `Product`.
One `Category` → many `Product`.

## Not modeled in this feature

- **Product images** are a separate related model (`ProductImage`: `product` FK, `image`
  `ImageField`, `position` for ordering) rather than a single field on `Product`, since spec FR-001
  allows "zero or more images." `on_delete=CASCADE` from `Product`.

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `product` | `ForeignKey(Product, related_name="images")`, `on_delete=CASCADE` | |
| `image` | `ImageField` | Stored via Django `Storage` API — research.md §1 |
| `position` | `PositiveSmallIntegerField`, default `0` | Display order on the detail page |

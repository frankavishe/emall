# Phase 0 Research: Product Catalog

All items below were open decisions in the Technical Context, not `[NEEDS CLARIFICATION]` markers
in spec.md — the spec's Assumptions section already fixed scope; this file fixes the *how*.

## 1. Product images: storage backend

**Decision**: Django `ImageField` (requires adding `Pillow` to `backend/requirements.txt`) backed
by Django's default `FileSystemStorage` to a local `backend/media/` directory for dev, served via
Django's dev static/media serving. Accessed through Django's `Storage` API, not hardcoded file
paths.

**Rationale**: Constitution Principle IV (Real Core, Mocked Edges) treats non-core external
integrations as swappable-but-real-in-shape. Image storage is exactly this class of concern —
using the `Storage` API means swapping to S3/Cloud Storage later (via `django-storages`) is a
settings change, not a rewrite, mirroring how `EmailService` was handled in 001-accounts-auth.

**Alternatives considered**: Storing image URLs only (no upload) — rejected, spec FR-001 requires
vendors to attach images as part of listing creation, not just link to externally-hosted ones.
Cloud storage integration now — rejected as premature for MVP scale (Scale/Scope: dozens of
products), adds a third-party account dependency the constitution says to avoid at this stage.

## 2. Search and filtering implementation

**Decision**: Manual queryset filtering in the catalog list view using Django ORM `Q` objects —
`icontains` on `name`/`description` for keyword search, exact match on `category`, `gte`/`lte` on
`price` for range — combined with `DEFAULT_PAGINATION_CLASS` already configured
(`PageNumberPagination`, `PAGE_SIZE: 20`).

**Rationale**: FR-008/FR-009 need keyword search plus category and price-range filtering,
combinable. The existing backend has zero query-building dependencies beyond DRF itself; a few
`Q` clauses in `get_queryset()` fully cover the requirement without adding `django-filter`.
Constitution Principle VI (Simplicity) — prefer the simplest implementation that satisfies the
requirement; three filter dimensions don't justify a new dependency.

**Alternatives considered**: `django-filter` — rejected, would be the first new runtime dependency
introduced solely for this feature's filtering, disproportionate to three simple filter axes.
Full-text search (Postgres `SearchVector`) — rejected as over-engineering for MVP scale; `icontains`
is sufficient at the stated dozens-of-products scale and avoids a Postgres-specific migration for
a v1 feature.

## 3. Category model

**Decision**: A separate `Category` model (`id`, `name` unique, `slug` unique) in the new
`apps/catalog` app, seeded via a Django data migration with a small fixed starter list (matching
the `seed_admin` management-command precedent from 001-accounts-auth, but as a migration since
categories are reference data, not an operational action).

**Rationale**: Spec Assumptions state categories are a global, Administrator-owned list, not
per-vendor free text — a real FK keeps filtering (FR-009) and product-name-uniqueness-per-shop
(FR-013, which is orthogonal to category) both queryable and consistent, versus a free-text
`CharField` that would let `"Electronics"` and `"electronics"` fragment the filter.

**Alternatives considered**: Free-text category field on `Product` — rejected, breaks exact-match
filtering (FR-009) and invites inconsistent values with no admin capability (explicitly out of
scope per Assumptions) to clean them up. A full admin CRUD UI for categories — rejected as out of
scope per spec Assumptions; a data migration is the simplest way to make categories exist without
building that UI now.

## 4. Soft delete for products

**Decision**: `Product` gets `is_deleted: BooleanField(default=False)` and `deleted_at:
DateTimeField(null=True)`. A custom default manager excludes `is_deleted=True` rows from all
normal querysets (vendor-facing and customer-facing); deletion is implemented as setting these two
fields, never `DELETE FROM`.

**Rationale**: Spec Assumptions explicitly call for soft delete to preserve referential integrity
for a future Orders feature that may reference a `Product` from historical order line items — this
directly serves Constitution Principle VI's requirement that per-line-item order fulfillment not be
foreclosed by earlier features.

**Alternatives considered**: Hard delete — rejected per spec Assumptions and the constitutional
concern above. A separate `deleted` boolean without manager-level filtering — rejected because it
would require every future query site to remember to filter it, an easy place to leak deleted
products into customer-facing views (violates FR-014).

## 5. Vendor product ownership + approval-gate enforcement

**Decision**: A new `IsApprovedShopOwnerForProduct` DRF permission class in `apps/catalog/
permissions.py`, mirroring the existing `apps/vendors/permissions.py::IsApprovedShopOwner` pattern:
`has_object_permission` checks `obj.shop.status == Shop.Status.APPROVED and obj.shop.owner_id ==
request.user.id`. For creation (no object yet), the serializer validates the target `shop_id` in
the payload against the same two conditions before the row is created.

**Rationale**: Reuses the exact pattern already established and reviewed in 001-accounts-auth
rather than inventing a new authorization shape — consistent per-shop (not per-account) enforcement
is the whole point of FR-002 / User Story 2, and the existing `IsApprovedShopOwner` proves the
pattern already satisfies Constitution Principle II in this codebase.

**Alternatives considered**: A single account-wide "is this user an approved vendor" check —
rejected outright, spec User Story 2 Scenario 3 explicitly requires per-shop enforcement (a Vendor
with one APPROVED and one PENDING shop can act on the former only).

## 6. Vendor product list pagination

**Decision**: Vendor-facing product list endpoint uses the project default
(`PageNumberPagination`, `PAGE_SIZE: 20`), unlike `GET /api/vendor/shops` which explicitly opts out
of pagination (`pagination_class = None`).

**Rationale**: The shops-list precedent was justified because "a vendor only ever has a handful of
shops" (001-accounts-auth plan notes). Products don't have that ceiling — an active shop can
plausibly exceed 20 listings well within MVP scope — so the default paginated behavior is the
correct, forward-safe choice here rather than copying the shops precedent by rote.

**Alternatives considered**: No pagination, matching shops — rejected for the reason above.

## 7. Frontend route namespace

**Decision**: New `frontend/src/app/vendor/products/` route namespace for vendor-side management
(list, create, edit), and `frontend/src/app/products/` for the public catalog (list + `[id]`
detail), both new top-level namespaces.

**Rationale**: Matches the existing `frontend/src/app/admin/...` precedent (a role-scoped
namespace) rather than overloading `frontend/src/app/account/`, which is a single profile page, not
a management console.

**Alternatives considered**: Nesting vendor product management under `/account/products` — rejected,
`/account` is scoped to the single-page profile view established in 001-accounts-auth and mixing in
a multi-page CRUD console there breaks that existing boundary.

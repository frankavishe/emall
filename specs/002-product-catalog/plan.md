# Implementation Plan: Product Catalog

**Branch**: `002-product-catalog` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-product-catalog/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Give approved Vendors a real product-listing back office (create/edit/publish/unpublish/delete,
scoped strictly to shops they own and gated per-shop on `Shop.status == APPROVED`) and give
Customers/visitors a real public catalog (browse, keyword search, category + price filter, product
detail) over exactly the published, non-deleted products of APPROVED shops. Implemented as a new
`apps/catalog` Django app (already named as a placeholder in 001-accounts-auth's plan) with
`Category` and `Product`/`ProductImage` models against PostgreSQL, a vendor-only DRF endpoint set
under `/api/vendor/products/`, a public read-only endpoint set under `/api/catalog/`, and two new
Next.js route namespaces (`/vendor/products`, `/products`). Product images use Django's `Storage`
API against local disk for dev (swappable later, per Constitution Principle IV). No new runtime
query-building dependency — search/filter is hand-rolled `Q`-object filtering, consistent with the
project's minimal-dependency pattern so far.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing), TypeScript 5.x / Node 20.x
(frontend, Next.js 16 App Router — existing)

**Primary Dependencies**: Django, Django REST Framework (existing). New: `Pillow` (required by
Django's `ImageField` for `ProductImage` — research.md §1). No new frontend dependencies.

**Storage**: PostgreSQL (Category, Product, ProductImage metadata — the "real core"); product image
*files* on local disk via Django's `FileSystemStorage` for dev, behind the `Storage` API so a real
backend (S3/Cloud Storage) is a later config change, not a rewrite (research.md §1).

**Testing**: `pytest` + `pytest-django` + `factory_boy` (existing pattern), DRF `APIClient` for
endpoint-level contract tests covering the approval-gate enforcement (FR-002) and validation rules
(FR-012/FR-013) as the highest-value test targets; frontend covered by manual quickstart
walkthroughs, matching 001-accounts-auth's approach.

**Target Platform**: Linux server (existing Django deployment target), any modern browser
(Next.js frontend)

**Project Type**: Web application (existing `backend/` + `frontend/` split; this feature adds
`backend/apps/catalog/` and two `frontend/src/app/` route namespaces)

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations (catalog list/search/detail responding well under 1s under local/dev load); SC-003's
"under 15 seconds" is a UX/interaction measure, not a backend latency target.

**Constraints**: Product create/publish re-validated server-side against `shop.status == APPROVED`
on every request (Constitution Principle II, FR-002) — never trusted from a prior check or the
client. Vendor product actions scoped to shops the acting Vendor owns (Constitution Principle I,
FR-006). Deletion is soft (`is_deleted`/`deleted_at`), never a hard DB delete, to keep the door open
for a future Orders feature to reference historical line items (Constitution Principle VI). Price
and stock quantity must reject negative values at the API boundary (FR-012).

**Scale/Scope**: Learning-project MVP scale (expected dozens of products across a handful of shops
during development, not a production load target); pagination is still applied by default
(research.md §6) so the design doesn't have to be revisited if that grows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Every vendor-mutation endpoint enforces role + shop-ownership server-side, never via client-side checks alone | **PASS** — `/api/vendor/products/*` requires `IsVendor` plus object-level `IsApprovedShopOwnerForProduct` (research.md §5); `/api/catalog/*` is intentionally public read-only with no role gate, matching its purpose |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | A shop not APPROVED cannot create/publish catalog listings, enforced server-side | **PASS** — `IsApprovedShopOwnerForProduct` re-checks `shop.status == APPROVED` on both create and publish (contracts/catalog-api.md), not just at shop-approval time; quickstart.md Scenario 2 exercises this via direct API call, bypassing the UI |
| III. Data & Payment Security | No plaintext secrets; no payment data touched by this feature | **PASS / N/A** — this feature introduces no new auth, payment, or secret-handling surface; image uploads are validated (type/size) at the serializer layer but carry no sensitive data |
| IV. Real Core, Mocked Edges | Schema, permission enforcement, and search/filter are fully real; only true externals may be stubbed | **PASS** — Category/Product/ProductImage schema, ownership/approval enforcement, and search/filter logic are fully implemented now; only the image storage *backend* (local disk vs. cloud) is swappable-but-real-in-shape, mirroring the 001-accounts-auth `EmailService` precedent |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — no code written in this phase; `/speckit-tasks` will order tasks by User Story 1 (P1, vendor mgmt) → User Story 2 (P1, gate enforcement, delivered alongside since it's inseparable from creation) → User Story 3 (P2, public browsing) |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not simplify away the three-role model, the shop approval state machine, or preclude future per-line-item order fulfillment | **PASS** — this feature only *reads* `Shop.status`, never redefines the state machine; `Product` is modeled as a standalone catalog entity (not embedded in any order concept), and soft-delete (research.md §4) exists specifically so a future Orders feature can reference a `Product` row from a historical line item without it having vanished |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: `research.md` and `data-model.md` decisions (reusing the
`IsApprovedShopOwner` permission pattern from 001-accounts-auth, soft-delete via manager-level
filtering, hand-rolled `Q`-object search instead of a new dependency, `Storage`-API-backed images)
were made specifically to satisfy the gates above, not around them — all six gates still **PASS**
after design.

## Project Structure

### Documentation (this feature)

```text
specs/002-product-catalog/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
│   └── catalog-api.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/                      # existing — no changes expected
│   ├── accounts/                  # existing — no changes expected
│   ├── vendors/                   # existing — Shop model referenced (FK target), no changes expected
│   ├── catalog/                   # THIS FEATURE (was a named placeholder in 001-accounts-auth's plan)
│   │   ├── models.py              # Category, Product, ProductImage
│   │   ├── serializers.py         # vendor (write) + public (read) serializers
│   │   ├── views.py               # VendorProductViewSet; public CatalogProductListView,
│   │   │                          # CatalogProductDetailView, CategoryListView
│   │   ├── urls.py                # vendor_urlpatterns (/api/vendor/products/) +
│   │   │                          # public urlpatterns (/api/catalog/)
│   │   ├── permissions.py         # IsApprovedShopOwnerForProduct
│   │   └── migrations/            # includes the Category seed data migration (research.md §3)
│   ├── cart/                      # future feature (not touched here)
│   ├── orders/                    # future feature (not touched here)
│   ├── payments/                  # future feature (not touched here)
│   └── feedback/                  # future feature (not touched here)
└── tests/
    └── catalog/                   # product CRUD, approval-gate, search/filter, validation tests

frontend/
├── src/
│   ├── app/
│   │   ├── vendor/
│   │   │   └── products/          # vendor product management (list, create, edit)
│   │   ├── products/              # public catalog
│   │   │   └── [id]/              # product detail page
│   │   └── ...                    # existing routes (account, admin, login, etc.) — unchanged
│   ├── lib/
│   │   ├── api-client.ts          # existing — reused, no changes expected
│   │   └── auth-context.tsx       # existing — reused, no changes expected
│   └── components/                # new: product card, filter bar (shared between vendor/public views if it makes sense at implementation time)
└── tests/
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split. This feature lives entirely in the new `backend/apps/catalog` app (which
001-accounts-auth's plan already reserved as a placeholder app boundary) plus two new Next.js route
namespaces, `frontend/src/app/vendor/products` and `frontend/src/app/products`. No existing app or
route is modified.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

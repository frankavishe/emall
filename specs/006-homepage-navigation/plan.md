# Implementation Plan: Role-Aware Homepage & Shared Navigation

**Branch**: `006-homepage-navigation` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-homepage-navigation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Replace the unmodified `create-next-app` boilerplate at `frontend/src/app/page.tsx` with a single
homepage whose content branches on `useAuth()`'s `user`/`role`/`shops`: guests get a marketing
view with recent-product highlights and Login/Register CTAs; Customers get recent products plus
links to cart/orders; Vendors get their shop's status (from `user.shops`, falling back to a
"request a shop" prompt) plus their shop's recent orders and a link to manage products; Admins get
a pending-shop-approval count plus recent platform orders and links into admin pages. A new shared
`Nav` component is added to `frontend/src/app/layout.tsx` so every page — not just the homepage —
has role-aware navigation. Every data source already exists (`/api/catalog/products`,
`/api/vendor/order-items`, `/api/admin/order-items`, `/api/admin/shops`, `/api/auth/me`); the only
backend change is a small shared DRF pagination class adding an opt-in `page_size` query param to
those four list views, so the homepage can request e.g. 8 products / 5 orders directly instead of
over-fetching the default page of 20 and slicing client-side. `login`/`register` are updated to
redirect to `/` instead of `/account` per the confirmed clarification.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing), TypeScript 5.x / Node 20.x
(frontend, Next.js 16 App Router — existing)

**Primary Dependencies**: Django, Django REST Framework (existing). No new runtime dependencies —
this feature is presentation plus one small, shared pagination-class change over data
001-accounts-auth, 002-product-catalog, 003-cart-checkout, and 004-order-fulfillment already
expose; no new frontend dependencies.

**Storage**: PostgreSQL — no schema changes. No new tables, no new columns.

**Testing**: `pytest` + `pytest-django` (existing pattern) for the one backend change (pagination
`page_size` opt-in, verified against the four affected list views: ordering unchanged, default
behavior unchanged when `page_size` is omitted, capped at a sane `max_page_size`). Frontend covered
by manual quickstart walkthroughs, matching 001-005's approach (no frontend automated test suite
exists in this repo).

**Target Platform**: Linux server (existing Django deployment target), any modern browser
(Next.js frontend)

**Project Type**: Web application (existing `backend/` + `frontend/` split). This feature adds no
new Django app; it extends `apps/core/` (shared pagination class, per the constitution's own
guidance that cross-app logic belongs in `core`) and adds new frontend components/pages only.

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations; the homepage issues at most 2 requests (one product/order list, one shop-status/
pending-count source) per role, all already-indexed queries ordered by existing indexes.

**Constraints**: Role-based content shown on the homepage/nav is a UI convenience only (per spec
FR-009 / constitution Principle I) — every list endpoint the homepage calls already enforces its
own server-side role/ownership filtering (`IsVendor` + `product__shop__owner=request.user` for
vendor order-items, `IsAdministrator` for admin endpoints, `AllowAny` + published/approved-only
filter for public catalog); this feature must not weaken any of that filtering while adding the
`page_size` param. The vendor shop-approval status shown on the homepage MUST come from already-
loaded `useAuth().user.shops` (no extra request) per research.md §2; if a rejection reason needs
display, a call to the existing `GET /api/vendor/shops` (not a new endpoint) supplies it.

**Scale/Scope**: Learning-project MVP scale, same as 001-005. Homepage widgets show small, fixed-
size slices (research.md §1 fixes the exact counts) of already-paginated data.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Homepage/nav branch client-side on `user.role`, but every underlying data call (`/api/catalog/products`, `/api/vendor/order-items`, `/api/admin/order-items`, `/api/admin/shops`) keeps its existing server-side permission class and queryset-level ownership filter unchanged | **PASS** — no new capability is exposed; the `page_size` addition only changes how many already-authorized rows come back, not which rows |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | Homepage must not let an unapproved Vendor's homepage imply they can list products/receive orders; it only reads and displays existing `Shop.status` | **PASS** — FR-004/FR-005 (spec.md) display status and, for PENDING/REJECTED/no-shop, redirect to the existing account-page request/resubmit flow rather than implying active selling capability |
| III. Data & Payment Security | No payment data touched by this feature | **PASS / N/A** |
| IV. Real Core, Mocked Edges | Homepage data must be real (not mocked/hardcoded placeholder content) | **PASS** — every section is backed by a real, existing, authenticated API call; no hardcoded fake data |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — `/speckit-tasks` will order by User Story 1 (P1, guest homepage) → User Story 2 (P1, shared nav) → User Story 3 (P2, customer homepage) → User Story 4 (P2, vendor homepage) → User Story 5 (P3, admin homepage) |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not collapse the three-role model, weaken the shop-approval gate, or touch per-line-item fulfillment status | **PASS** — this feature is purely a read/presentation layer; it introduces no new role concept (e.g. no "guest" role added to the backend), no change to `Shop.status` transitions, and no change to `OrderItem` status handling |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: research.md's decisions (shared opt-in `page_size` pagination param
applied to four existing views rather than four new endpoints; reading Vendor shop status from
already-loaded `useAuth().user.shops` rather than an extra request; reusing DRF's existing
paginated-envelope `count` field for the admin pending-shop count rather than a new count
endpoint) keep every gate above **PASS** after design — no new endpoints, no new models, no change
to any existing permission class.

## Project Structure

### Documentation (this feature)

```text
specs/006-homepage-navigation/
├── plan.md                # This file (/speckit-plan command output)
├── research.md             # Phase 0 output (/speckit-plan command)
├── data-model.md           # Phase 1 output (/speckit-plan command)
├── quickstart.md           # Phase 1 output (/speckit-plan command)
├── contracts/              # Phase 1 output (/speckit-plan command)
│   └── homepage-api.md
├── checklists/
│   └── requirements.md     # already exists (spec quality checklist)
└── tasks.md                # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/
│   │   └── pagination.py           # NEW — shared PageNumberPagination subclass with opt-in
│   │                                #   page_size query param (capped by max_page_size)
│   ├── catalog/
│   │   └── views.py                # extended — CatalogProductListView.pagination_class = new class
│   ├── vendors/
│   │   └── views.py                # extended — AdminShopListView.pagination_class = new class
│   │                                #   (VendorShopListCreateView untouched — already unpaginated,
│   │                                #    already returned via /api/auth/me for homepage purposes)
│   ├── orders/
│   │   └── views.py                # extended — VendorOrderItemListView, AdminOrderItemListView
│   │                                #   .pagination_class = new class
│   └── ...                         # accounts, cart, payments, feedback — no changes
└── tests/
    └── core/
        └── test_pagination.py      # NEW — page_size honored, capped, default unchanged when omitted

frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx                # REWRITTEN — role-aware homepage (guest/customer/vendor/admin)
│   │   ├── layout.tsx              # extended — renders new <Nav /> above {children}
│   │   ├── login/page.tsx          # extended — router.push("/account") → router.push("/")
│   │   └── register/page.tsx       # extended — router.push("/account") → router.push("/")
│   ├── components/
│   │   ├── nav.tsx                 # NEW — shared role-aware navigation bar
│   │   └── star-rating.tsx         # existing — unchanged
│   └── lib/
│       └── api-client.ts           # extended — new thin wrappers: listProducts(limit?),
│                                    #   listVendorOrderItems(page?, limit?) [existing fn gains
│                                    #   optional limit], listAdminOrderItems(..., limit?)
│                                    #   [existing fn gains optional limit], listAdminShops(status?,
│                                    #   limit?) [new — admin/shops/page.tsx keeps its own inline
│                                    #   call or is migrated to this wrapper at implementer's
│                                    #   discretion during /speckit-tasks]
└── tests/                          # none exist today (see Testing above) — no change
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split. No new Django app is added; the one backend change (shared pagination
class) lives in `apps/core/`, matching the constitution's explicit rule that cross-app logic
belongs there. All new frontend work is additive (`components/nav.tsx`, rewritten `page.tsx`,
small `api-client.ts` extensions) — no existing page's role-gating logic or route structure
changes except the two redirect-target edits in `login`/`register`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

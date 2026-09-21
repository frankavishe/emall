# Implementation Plan: Vendor Order Fulfillment

**Branch**: `004-order-fulfillment` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-order-fulfillment/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Give a Vendor a way to see and act on the `OrderItem` lines that belong to their own shop's
products (across all Customers' orders), advancing each line through a fulfillment lifecycle —
PENDING → PROCESSING → SHIPPED → DELIVERED, or CANCELLED as an alternate terminal state from
PENDING/PROCESSING — strictly scoped to their own shop and strictly forward-only. This extends the
`OrderItem.status` field 003-cart-checkout already introduced (currently only `PENDING` is
reachable) rather than adding a new entity; a new `OrderItemStatusEvent` history model records
every change for Administrator-only audit visibility. Cancelling a line restores its quantity to
the product's stock inside the same atomic transaction as the status change, mirroring
`place_order()`'s existing `select_for_update()` pattern to avoid races with concurrent checkouts.
The Customer-facing per-line status (User Story 2) needs **no new work** — `orders/[id]/page.tsx`
and `OrderItemSerializer` already render `item.status` per line from 003-cart-checkout; this
feature only needs to make that field move. New surfaces: a Vendor fulfillment queue
(`GET`/`PATCH /api/vendor/order-items`) and an Administrator read-only oversight view
(`GET /api/admin/order-items`, including history), both new Next.js pages.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing), TypeScript 5.x / Node 20.x
(frontend, Next.js 16 App Router — existing)

**Primary Dependencies**: Django, Django REST Framework (existing). No new runtime dependencies —
this feature is pure domain logic over data 003-cart-checkout already created; no new frontend
dependencies.

**Storage**: PostgreSQL — extends the existing `OrderItem` row (widens `status` choices, no schema
change to existing columns) and adds one new table, `OrderItemStatusEvent` (order_item FK, status,
changed_at), both real schema/migrations (Constitution Principle IV).

**Testing**: `pytest` + `pytest-django` + `factory_boy` (existing pattern), DRF `APIClient` for
endpoint-level contract tests covering the Vendor fulfillment list/update (valid transitions,
rejected invalid transitions, cross-vendor isolation), the Customer-visible status field
(regression-only, since the page/serializer already exist), the Administrator oversight view
(read-only enforcement, history inclusion), and the stock-restoration-on-cancel behavior including
a concurrency check mirroring `test_checkout_concurrency.py`'s pattern; frontend covered by manual
quickstart walkthroughs, matching 001/002/003's approach.

**Target Platform**: Linux server (existing Django deployment target), any modern browser
(Next.js frontend)

**Project Type**: Web application (existing `backend/` + `frontend/` split; this feature adds new
surface to the existing `backend/apps/orders/` app plus two new `frontend/src/app/` route
namespaces — no new Django app, since the constitution's app list (`accounts, vendors, catalog,
cart, orders, payments, feedback, core`) has no separate "fulfillment" app; order-line fulfillment
is order-domain logic)

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations; SC-001's "within a few seconds" is a UX/interaction measure, not a backend latency
target.

**Constraints**: Status transitions MUST be validated server-side against the exact adjacency rule
in FR-002/FR-003 (single forward step, or CANCELLED from PENDING/PROCESSING only) — never trusted
from client-sent target status alone. Stock restoration on cancellation MUST be atomic with the
status change (FR-011) so a crash between the two never leaves stock under-restored or a line
CANCELLED without its stock back (Constitution "Reliability" NFR). Every Vendor-facing query MUST
filter to that Vendor's own shops' products at the queryset level (FR-004), not only via
object-level permission checks on a single object.

**Scale/Scope**: Learning-project MVP scale, same as 001–003; the Vendor fulfillment list and
Administrator oversight list are both paginated by default, consistent with the existing
`OrderListView`/`CatalogProductListView` precedent.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Vendor fulfillment endpoints require `role == VENDOR` server-side and are filtered to that Vendor's own shops at the queryset level; Administrator oversight requires `role == ADMINISTRATOR`; Customer visibility reuses the existing `IsCustomer`-gated order-detail endpoint unchanged | **PASS** — new `apps.orders.permissions.IsOrderItemShopOwner` (mirrors `apps.catalog.permissions.IsProductOwner`/`IsApprovedShopOwnerForProduct`) plus `.filter(product__shop__owner=request.user)` on the Vendor list queryset (research.md), never a client-supplied vendor/shop id |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | A Vendor whose shop is not APPROVED MUST NOT be able to advance fulfillment status (FR-010) | **PASS** — the status-update endpoint additionally checks `obj.product.shop.status == Shop.Status.APPROVED`, reusing the exact pattern of `IsApprovedShopOwnerForProduct`; a non-APPROVED shop's lines remain visible (read) but not mutable, same asymmetry as catalog's `IsProductOwner` vs `IsApprovedShopOwnerForProduct` |
| III. Data & Payment Security | This feature touches no payment fields | **PASS / N/A** — `PaymentRecord` is untouched; cancellation does not create, modify, or reference any payment/refund data (spec Assumptions) |
| IV. Real Core, Mocked Edges | Status-transition enforcement and stock restoration are core order-lifecycle correctness, MUST be fully real | **PASS** — no mocking applies here (no external integration); the transition state machine and stock restoration are real service-layer logic, transactional, tested with contract + concurrency tests |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — no code written in this phase; `/speckit-tasks` will order tasks by User Story 1 (P1, Vendor view+advance) → User Story 2 (P1, Customer visibility — verification-only, already built) → User Story 3 (P3, Administrator oversight) |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not collapse per-line-item fulfillment status back to an order-level status, and must not simplify away the multi-vendor independence the constitution names explicitly | **PASS** — this feature is the direct continuation of the `OrderItem.status` field the constitution requires to exist per-line (Principle VI); FR-005 explicitly keeps status per-line on the Customer's order view rather than rolling it up |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: `research.md` and `data-model.md` decisions (queryset-level shop
ownership filtering reused from the catalog/vendor precedent, `select_for_update()` reused from
`place_order()` for the stock-restoration race, `OrderItemStatusEvent` as a genuinely new but
minimal append-only table, and no change to the Customer-facing serializer/page) were made
specifically to satisfy the gates above, not around them — all six gates still **PASS** after
design.

## Project Structure

### Documentation (this feature)

```text
specs/004-order-fulfillment/
├── plan.md                # This file (/speckit-plan command output)
├── research.md            # Phase 0 output (/speckit-plan command)
├── data-model.md          # Phase 1 output (/speckit-plan command)
├── quickstart.md          # Phase 1 output (/speckit-plan command)
├── contracts/              # Phase 1 output (/speckit-plan command)
│   └── order-fulfillment-api.md
├── checklists/
│   └── requirements.md    # already exists (spec quality checklist)
└── tasks.md                # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/                      # existing — no changes expected
│   ├── accounts/                  # existing — no changes expected
│   ├── vendors/                   # existing — Shop model referenced (FK target), no changes expected
│   ├── catalog/                   # existing — Product.stock_quantity restored on cancel, no changes expected
│   ├── cart/                      # existing — no changes expected
│   ├── payments/                  # existing — no changes expected (spec Assumptions: no payment/refund coupling)
│   └── orders/                    # THIS FEATURE (extends the existing app, no new app)
│       ├── models.py              # OrderItem.Status widened (PROCESSING/SHIPPED/DELIVERED/CANCELLED
│       │                          #   added to existing PENDING); new OrderItemStatusEvent(order_item, status, changed_at)
│       ├── permissions.py         # NEW — IsOrderItemShopOwner (mirrors apps.catalog.permissions)
│       ├── serializers.py         # extended — VendorOrderItemSerializer, AdminOrderItemSerializer
│       │                          #   (+ history), OrderItemStatusUpdateSerializer
│       ├── services.py            # extended — advance_order_item_status() (transition validation +
│       │                          #   atomic stock restoration on CANCELLED, mirrors place_order()'s
│       │                          #   select_for_update() pattern)
│       ├── views.py               # extended — VendorOrderItemListView, VendorOrderItemStatusUpdateView,
│       │                          #   AdminOrderItemListView
│       └── urls.py                # extended — new vendor_urlpatterns, admin_urlpatterns lists
└── tests/
    └── orders/                    # extended — vendor fulfillment list/update, cross-vendor isolation,
                                    #   invalid-transition rejection, stock-restoration + concurrency,
                                    #   admin oversight read-only + history, customer-visibility regression

frontend/
├── src/
│   ├── app/
│   │   ├── orders/[id]/           # existing — already renders item.status per line (spec Summary),
│   │   │                          #   no change expected
│   │   ├── vendor/
│   │   │   └── orders/            # NEW — Vendor fulfillment queue (list + advance/cancel action)
│   │   ├── admin/
│   │   │   └── orders/            # NEW — Administrator read-only oversight view (+ history)
│   │   └── ...                    # existing routes — unchanged
│   ├── lib/
│   │   └── api-client.ts          # existing — extended with listVendorOrderItems, updateOrderItemStatus,
│   │                              #   listAdminOrderItems (matches the checkout/listOrders/getOrder
│   │                              #   wrapper-function precedent already in this file)
│   └── components/                # new: fulfillment status badge/action control (shared vendor/admin views)
└── tests/
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split. This feature adds no new Django app — it extends the existing
`backend/apps/orders/` app, since fulfillment status is order-line domain logic the constitution
already scopes there (Principle VI's per-line-item status lives on `OrderItem`). Two new Next.js
route namespaces (`vendor/orders`, `admin/orders`); the existing Customer `orders/[id]` page is
unchanged.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

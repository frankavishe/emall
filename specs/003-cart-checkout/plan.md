# Implementation Plan: Shopping Cart & Checkout

**Branch**: `003-cart-checkout` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-cart-checkout/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Give a logged-in Customer a persistent, server-side cart over the existing `002-product-catalog`
`Product` model, and a checkout flow that turns a validated cart into a real `Order` (with
per-vendor-line fulfillment status, per Constitution Principle VI) via a mocked, swappable payment
step. Implemented as three new Django apps — `apps/cart` (`Cart`, `CartItem`), `apps/orders`
(`Order`, `OrderItem`, checkout orchestration), `apps/payments` (`PaymentRecord`, a
`PaymentService` interface with one mock implementation, mirroring `EmailService` from
001-accounts-auth) — all three already named as future placeholders in 002-product-catalog's plan.
Cart line prices are never frozen (live-read from `Product` per User Story 3); checkout
re-validates every line server-side (stock, published, shop still APPROVED) inside one atomic
transaction with row locks, so stock decrement and Order creation succeed or fail together
(FR-014). New Next.js routes: `/cart`, `/checkout`, `/orders`, `/orders/[id]`, plus a minimal
"Add to Cart" addition to the existing `/products` and `/products/[id]` pages.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing), TypeScript 5.x / Node 20.x
(frontend, Next.js 16 App Router — existing)

**Primary Dependencies**: Django, Django REST Framework (existing). No new runtime dependencies —
payment is fully mocked in-process (research.md §5), no gateway SDK needed. No new frontend
dependencies.

**Storage**: PostgreSQL — `Cart`, `CartItem`, `Order`, `OrderItem`, `PaymentRecord` are all real
schema/rows (Constitution Principle IV "real core"); nothing about the cart→checkout→order
lifecycle itself is mocked, only the payment gateway call is.

**Testing**: `pytest` + `pytest-django` + `factory_boy` (existing pattern), DRF `APIClient` for
endpoint-level contract tests covering cart CRUD, the checkout happy path (single- and
multi-vendor carts), every checkout rejection path (empty cart, stale price/stock/publish/approval,
payment decline, missing shipping field), and order-history ownership isolation as the
highest-value test targets; frontend covered by manual quickstart walkthroughs, matching
001/002's approach.

**Target Platform**: Linux server (existing Django deployment target), any modern browser
(Next.js frontend)

**Project Type**: Web application (existing `backend/` + `frontend/` split; this feature adds
`backend/apps/cart/`, `backend/apps/orders/`, `backend/apps/payments/`, and four new
`frontend/src/app/` route namespaces)

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations; SC-002's "under 3 minutes" is a UX/interaction measure, not a backend latency target.

**Constraints**: Every cart line and the checkout request as a whole MUST be re-validated against
*current* `Product`/`Shop` state at checkout time, never trusted from when the line was added
(FR-008, User Story 3). Stock decrement and Order creation MUST be all-or-nothing
(FR-014) — enforced via `transaction.atomic()` plus `select_for_update()` on the touched `Product`
rows to close the concurrent-checkout oversell race (Edge Cases). Payment mock MUST NOT store raw
card data even hypothetically (Constitution Principle III) — it never accepts card fields at all,
only an opaque method label.

**Scale/Scope**: Learning-project MVP scale, same as 002-product-catalog; pagination applied by
default on cart-independent list endpoints (order history) so the design doesn't need revisiting
if that grows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Every cart/checkout/order endpoint requires `role == CUSTOMER` server-side, and every queryset is filtered to `request.user` — never trusted from the client | **PASS** — `apps.core.permissions.IsCustomer` gates all endpoints; `Cart`/`Order` querysets filter by `customer=request.user` at the queryset level (research.md §6), not only in serializers, per the Security & Non-Functional Requirements section |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | A shop that is no longer APPROVED cannot receive new orders, enforced server-side at checkout, not just at add-to-cart time | **PASS** — checkout re-validates `product.shop.status == APPROVED` per line at commit time (FR-008, data-model.md), blocking checkout and flagging the specific line if a shop was un-approved after the item was added (Edge Cases) |
| III. Data & Payment Security | No raw card data anywhere, including the mock | **PASS** — `PaymentService.charge()` accepts only an opaque method label, never card fields; `PaymentRecord` stores only method, status, and a generated opaque `transaction_reference` (research.md §5) |
| IV. Real Core, Mocked Edges | Cart/checkout/order schema, permission enforcement, and stock-decrement logic are fully real; only the payment gateway is mocked, and as a swappable interface | **PASS** — `Cart`, `Order`, `OrderItem` schema and the atomic checkout transaction (research.md §4) are fully implemented now; `PaymentService` (research.md §5) mirrors the `EmailService` precedent from 001-accounts-auth exactly — one ABC, one `MockPaymentService`, swappable via a factory function |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — no code written in this phase; `/speckit-tasks` will order tasks by User Story 1 (P1, cart) → User Story 2 (P1, checkout, depends on US1) → User Story 3 (P2, live-data correctness, woven through US1/US2's read paths) → User Story 4 (P3, order history) |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not simplify away per-line-item order fulfillment status, and must not build speculative vendor-fulfillment UI this feature doesn't need | **PASS** — `OrderItem.status` exists now (data-model.md) because a single Order can span multiple vendors' shops (FR-013) and Constitution Principle VI names this structural element explicitly; no endpoint to *mutate* that status is built here (vendor fulfillment management is explicitly out of scope per spec Assumptions) — the field exists because a future feature needs it to already be there, not as speculative extra surface |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: `research.md` and `data-model.md` decisions (queryset-level ownership
filtering reused from the catalog/vendor precedent, `select_for_update()` for the oversell race,
the `PaymentService` swappable-mock pattern reused verbatim from `EmailService`, and
`OrderItem.status` included without a mutating endpoint) were made specifically to satisfy the
gates above, not around them — all six gates still **PASS** after design.

## Project Structure

### Documentation (this feature)

```text
specs/003-cart-checkout/
├── plan.md               # This file (/speckit-plan command output)
├── research.md            # Phase 0 output (/speckit-plan command)
├── data-model.md          # Phase 1 output (/speckit-plan command)
├── quickstart.md          # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   └── cart-checkout-api.md
├── checklists/
│   └── requirements.md    # already exists (spec quality checklist)
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/                      # existing — no changes expected
│   ├── accounts/                  # existing — no changes expected
│   ├── vendors/                   # existing — Shop model referenced (FK target), no changes expected
│   ├── catalog/                   # existing — Product model referenced (FK target), no changes expected
│   ├── cart/                      # THIS FEATURE (was a named placeholder in 002-product-catalog's plan)
│   │   ├── models.py              # Cart, CartItem
│   │   ├── serializers.py         # live-priced cart/line serializers (research.md §2)
│   │   ├── views.py               # CartDetailView, CartItemCreateView, CartItemDetailView
│   │   └── urls.py                # /api/cart/, /api/cart/items/, /api/cart/items/{id}/
│   ├── orders/                    # THIS FEATURE
│   │   ├── models.py              # Order, OrderItem
│   │   ├── serializers.py         # checkout request/response, order list/detail
│   │   ├── services.py            # place_order() — the atomic checkout transaction (research.md §4)
│   │   ├── views.py               # CheckoutView, OrderListView, OrderDetailView
│   │   └── urls.py                # /api/checkout/, /api/orders/, /api/orders/{id}/
│   ├── payments/                  # THIS FEATURE
│   │   ├── models.py              # PaymentRecord
│   │   └── services.py            # PaymentService (ABC), MockPaymentService (research.md §5)
│   └── feedback/                  # future feature (not touched here)
└── tests/
    ├── cart/                      # cart CRUD, ownership isolation, live-pricing/availability
    └── orders/                    # checkout happy/rejection paths, order history

frontend/
├── src/
│   ├── app/
│   │   ├── cart/                  # view/edit cart (quantity change, remove line)
│   │   ├── checkout/              # shipping form + confirm + payment step (mocked)
│   │   ├── orders/                # order history list
│   │   │   └── [id]/              # order detail / confirmation
│   │   ├── products/              # existing — minimal "Add to Cart" addition, no restructuring
│   │   └── ...                    # existing routes — unchanged
│   ├── lib/
│   │   ├── api-client.ts          # existing — reused, add cart/checkout/order calls
│   │   └── auth-context.tsx       # existing — reused, no changes expected
│   └── components/                # new: cart line item, checkout shipping form (shared where useful)
└── tests/
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split. This feature lives in three new `backend/apps/{cart,orders,payments}`
apps (all three already reserved as placeholder app boundaries in 002-product-catalog's plan) plus
four new Next.js route namespaces. No existing app or route is restructured; `/products` and
`/products/[id]` get an additive "Add to Cart" control only.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

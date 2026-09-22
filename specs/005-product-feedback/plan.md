# Implementation Plan: Product Feedback & Reviews

**Branch**: `005-product-feedback` | **Date**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-product-feedback/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Give a Customer a way to leave a 1-5 star rating and optional written comment on a product they
have actually received (`OrderItem.status == DELIVERED`, reusing 004-order-fulfillment's
lifecycle), surface those reviews and an aggregate average rating/count on the existing public
product detail page for any shopper, give a Vendor a read-only view of feedback scoped to their
own shop's products, and give an Administrator a read-only view across every shop plus the ability
to remove an individual review. This introduces one new Django app, `apps/feedback/`, with a
single new `Review` model (at most one per Customer/Product pair, enforced by a DB constraint) —
the constitution's own app-boundary list already names `feedback` as an established boundary with
no code in it yet. No existing app's schema changes; `catalog.Product` and `orders.OrderItem` are
only read from. New surfaces: `POST`/`DELETE /api/feedback/products/{id}/review/` (Customer),
`GET /api/vendor/reviews/` (Vendor), `GET`/`DELETE /api/admin/reviews/` (Administrator), two new
fields on the existing public catalog serializers, and one new Next.js page each for the Vendor and
Administrator views plus a reviews section added to the existing product detail page.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing), TypeScript 5.x / Node 20.x
(frontend, Next.js 16 App Router — existing)

**Primary Dependencies**: Django, Django REST Framework (existing). No new runtime dependencies —
this feature is pure domain logic (a new model + read/write endpoints) over data 002-product-
catalog and 004-order-fulfillment already created; no new frontend dependencies.

**Storage**: PostgreSQL — adds one new table, `feedback_review` (customer FK, product FK, rating,
comment, timestamps, unique-together + range constraints; data-model.md). No changes to any
existing table's columns.

**Testing**: `pytest` + `pytest-django` + `factory_boy` (existing pattern), new `ReviewFactory` and
`OrderItemFactory` in `tests/factories.py` (research.md §7 — the latter fills a gap
004-order-fulfillment's tests worked around rather than filled), DRF `APIClient` for
endpoint-level contract tests (eligibility gate, upsert semantics, public read + aggregate, vendor
scoping, admin list + delete); frontend covered by manual quickstart walkthroughs, matching
001-004's approach (no frontend automated test suite exists in this repo).

**Target Platform**: Linux server (existing Django deployment target), any modern browser
(Next.js frontend)

**Project Type**: Web application (existing `backend/` + `frontend/` split; this feature adds a new
Django app `backend/apps/feedback/` — the constitution's app list explicitly names `feedback` as
an established, not-yet-built boundary — plus new `frontend/src/app/` route additions; no changes
to `apps/catalog/` or `apps/orders/` models)

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations; the rating aggregate (research.md §4) is a single indexed `AVG`/`COUNT` query per
product read, consistent with this project's existing learning-project MVP scale.

**Constraints**: Review eligibility MUST be re-checked server-side against live `OrderItem` data on
every create/update (research.md §2), never trusted from a client-supplied flag. At most one
Review per (Customer, Product) MUST be enforced at the database level (data-model.md), not only in
application code. A Vendor's/Administrator's review queries MUST filter at the queryset level to
the requester's own shop's products (Vendor) or unrestricted (Administrator), matching the
queryset-filtering pattern already established in `apps/catalog/views.py` — never object-level
checks alone.

**Scale/Scope**: Learning-project MVP scale, same as 001-004; the Vendor and Administrator review
list endpoints are both paginated by default, consistent with the existing
`VendorProductListCreateView`/`AdminShopListView` precedent.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Review write endpoints require `role == CUSTOMER`; Vendor feedback view requires `role == VENDOR` and is filtered to that Vendor's own shops at the queryset level; Administrator moderation requires `role == ADMINISTRATOR`; public read requires no role | **PASS** — reuses existing `apps.core.permissions.IsCustomer/IsVendor/IsAdministrator` and the `product__shop__owner=request.user` queryset-filter pattern from `apps/catalog/views.py` (research.md §5), never a client-supplied shop/vendor id |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | Not applicable to this feature's write path (Vendors have read-only access here) — but worth confirming reviews aren't blocked/unblocked by shop approval status in a way that would leak or hide feedback incorrectly | **PASS / N/A** — FR-013 explicitly keeps Vendor read access to feedback independent of current shop-approval status (feedback already earned while approved shouldn't vanish if the shop is later un-approved); this feature adds no new capability gated by Principle II since Vendors cannot create/publish/sell anything here |
| III. Data & Payment Security | This feature touches no payment fields or payment data | **PASS / N/A** — `Review` has no relationship to `payments.PaymentRecord`; only reads `orders.OrderItem.status` (non-payment field) to check eligibility |
| IV. Real Core, Mocked Edges | Purchase-verification gating and the one-review-per-customer-per-product constraint are core correctness, MUST be fully real | **PASS** — no mocking applies (no external integration involved); the DELIVERED-status check and the DB uniqueness constraint are both real, tested with contract tests, not stubbed |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — no code written in this phase; `/speckit-tasks` will order tasks by User Story 1 (P1, Customer submits review) → User Story 2 (P1, public visibility) → User Story 3 (P2, Vendor view) → User Story 4 (P3, Administrator moderation) |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not collapse the three-role model, must not weaken the shop approval gate, and must not undermine per-line-item fulfillment status (the three load-bearing structures Principle VI protects) | **PASS** — this feature adds a new, independent entity that reads `OrderItem.status` but doesn't modify the fulfillment state machine, doesn't touch shop approval, and preserves the three-role model (Customer writes, Vendor reads own-shop, Administrator reads-all + moderates) |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: `research.md` and `data-model.md` decisions (a new `feedback` app rather
than bolting onto `catalog`/`orders`, a live re-query against `OrderItem` rather than a cached
eligibility flag, an upsert endpoint backed by a DB uniqueness constraint, on-read rating
aggregation rather than denormalized fields, queryset-level Vendor/Administrator scoping reusing
the existing precedent, and a hard delete for moderation per the spec's own Assumptions) were made
specifically to satisfy the gates above, not around them — all six gates still **PASS** after
design.

## Project Structure

### Documentation (this feature)

```text
specs/005-product-feedback/
├── plan.md                # This file (/speckit-plan command output)
├── research.md             # Phase 0 output (/speckit-plan command)
├── data-model.md           # Phase 1 output (/speckit-plan command)
├── quickstart.md           # Phase 1 output (/speckit-plan command)
├── contracts/              # Phase 1 output (/speckit-plan command)
│   └── feedback-api.md
├── checklists/
│   └── requirements.md     # already exists (spec quality checklist)
└── tasks.md                # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/                      # existing — no changes expected
│   ├── accounts/                  # existing — no changes expected
│   ├── vendors/                   # existing — Shop referenced (via product.shop), no changes expected
│   ├── catalog/                   # existing — serializers extended (see below); model unchanged
│   ├── cart/                      # existing — no changes expected
│   ├── orders/                    # existing — OrderItem read from (eligibility check), no changes expected
│   ├── payments/                  # existing — no changes expected
│   └── feedback/                  # NEW APP — this feature
│       ├── models.py              # NEW — Review(customer FK, product FK, rating, comment, timestamps)
│       ├── permissions.py         # NEW — eligibility check helper (has_delivered_purchase), reuses
│       │                          #   apps.core.permissions.IsCustomer/IsVendor/IsAdministrator for role gating
│       ├── serializers.py         # NEW — ReviewWriteSerializer, VendorReviewSerializer, AdminReviewSerializer
│       ├── views.py                # NEW — CustomerReviewView (POST/DELETE), VendorReviewListView,
│       │                          #   AdminReviewListView, AdminReviewDeleteView
│       └── urls.py                 # NEW — urlpatterns, vendor_urlpatterns, admin_urlpatterns (mirrors
│                                    #   apps/catalog/urls.py's split)
├── apps/catalog/
│   └── serializers.py              # extended — CatalogProductListSerializer/CatalogProductDetailSerializer
│                                    #   gain average_rating/review_count (list+detail) and reviews (detail only)
├── config/
│   ├── settings.py                 # extended — "apps.feedback" added to INSTALLED_APPS
│   └── urls.py                     # extended — new feedback urlpatterns mounted at /api/feedback/,
│                                    #   /api/vendor/, /api/admin/ alongside existing includes
└── tests/
    └── feedback/                   # NEW — eligibility gate (delivered/not-delivered), upsert semantics,
                                     #   uniqueness constraint, public read + aggregate (incl. zero-review
                                     #   case), vendor scoping, admin list + delete + post-delete
                                     #   recalculation

frontend/
├── src/
│   ├── app/
│   │   ├── products/[id]/          # existing — extended with a reviews section + submit-review form
│   │   │                          #   (visible to any shopper; form shown/enabled only for eligible
│   │   │                          #   logged-in Customers)
│   │   ├── vendor/
│   │   │   └── reviews/            # NEW — Vendor feedback view (read-only list)
│   │   ├── admin/
│   │   │   └── reviews/            # NEW — Administrator moderation view (list + remove action)
│   │   └── ...                     # existing routes — unchanged
│   ├── lib/
│   │   └── api-client.ts           # existing — extended with submitReview, deleteReview,
│   │                              #   listVendorReviews, listAdminReviews, deleteReviewAsAdmin
│   │                              #   (matches the listVendorOrderItems/updateOrderItemStatus
│   │                              #   wrapper-function precedent from 004-order-fulfillment)
│   └── components/                 # new: star-rating display + input, review list item (shared
│                                    #   across product page / vendor view / admin view)
└── tests/
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split. This feature adds exactly one new Django app,
`backend/apps/feedback/`, matching the constitution's own named app boundary
(`accounts, vendors, catalog, cart, orders, payments, feedback, core`) rather than bolting a new
entity onto `catalog` or `orders`. The existing public product detail page and its serializers are
extended in place (no new customer-facing route for reading reviews); two new Next.js route
namespaces (`vendor/reviews`, `admin/reviews`) are added, mirroring 004-order-fulfillment's
`vendor/orders`/`admin/orders` precedent.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

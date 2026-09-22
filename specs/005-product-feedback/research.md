# Research: Product Feedback & Reviews

No NEEDS CLARIFICATION markers remain in the Technical Context (see plan.md) — this feature reuses
the existing Django/DRF + Next.js stack, existing role/permission machinery, and existing
`OrderItem` fulfillment data with no new technology choices. This document records the design
decisions made while resolving open questions from the spec, each phrased as Decision/Rationale/
Alternatives per the plan workflow.

## 1. New Django app vs. extending an existing app

**Decision**: Create a new `backend/apps/feedback/` app with its own `Review` model.

**Rationale**: The constitution's Maintainability bullet names `feedback` explicitly as one of the
established app boundaries (`accounts, vendors, catalog, cart, orders, payments, feedback, core`)
— it's the one app in that list with no code yet. A `Review` is also a genuinely new entity (not
an extension of an existing one, unlike 004-order-fulfillment which widened `OrderItem`), so it
warrants its own app rather than being bolted onto `catalog` or `orders`.

**Alternatives considered**:
- Add `Review` to `apps/catalog/` (reviews are about products) — rejected: couples an
  unrelated domain concept (customer opinion) into the product-listing app, and abandons the
  constitution's own named app boundary for no benefit.
- Add `Review` to `apps/orders/` (reviews are gated by an order line) — rejected for the same
  reason; the qualifying `OrderItem` is a reference, not a concept `orders` needs to own.

## 2. Purchase-verification query

**Decision**: Eligibility is computed with a single queryset check at submission time —
`OrderItem.objects.filter(order__customer=customer, product=product, status=OrderItem.Status.DELIVERED).exists()`
— re-checked on every create/update, not cached or stored as a boolean flag on the Review.

**Rationale**: `OrderItem.status` already carries exactly this signal (004-order-fulfillment).
Re-checking at write time (rather than trusting a client-supplied "I purchased this" flag or a
cached eligibility bit) keeps the enforcement server-side per Constitution Principle I and avoids
a second source of truth that could desync from the real fulfillment state.

**Alternatives considered**:
- Store a `qualifying_order_item` FK on `Review` and trust it going forward — rejected: adds a
  nullable FK to track state the live query already answers correctly and cheaply (indexed
  `order__customer` + `product` lookup), and the spec's edge case (a different DELIVERED line
  still qualifies the customer even if the original qualifying line is later cancelled) is
  naturally satisfied by re-querying rather than pinning to one specific line item.

## 3. One review per (Customer, Product): create-or-update semantics

**Decision**: `POST /api/feedback/products/{product_id}/review` is an upsert — creates the
Review if none exists for that (customer, product) pair, otherwise updates the existing one's
rating/comment. Enforced with a `unique_together`/`UniqueConstraint` on `(customer, product)` at
the database level as the actual guarantee, with the view doing a `get_or_create`-style lookup
first so a second submission returns `200` (update) rather than a `409` from the constraint.

**Rationale**: FR-003 requires "at most one review per Customer per product" with a repeat
submission updating rather than duplicating. A single upsert endpoint matches the spec's
description of the user action ("leave a rating and review") better than exposing separate
create/update endpoints the frontend would have to choose between based on prior state it doesn't
otherwise need to track.

**Alternatives considered**:
- Separate `POST` (create, 409 if exists) and `PATCH /{review_id}` (update) — rejected: forces the
  Customer-facing product page to first know whether a review already exists (an extra request) to
  pick the right verb; the upsert endpoint is simpler for the one real user action ("leave/update
  my review") and the DB constraint still prevents duplicates regardless of view-layer bugs.

## 4. Rating aggregation (average + count)

**Decision**: Compute the average rating and review count on read, via a DB aggregate
(`Review.objects.filter(product=product).aggregate(Avg("rating"), Count("id"))`) inside the
existing `CatalogProductDetailSerializer`/`CatalogProductListSerializer`, not as a stored/denormalized
field on `Product`.

**Rationale**: Matches FR-006's "recalculated whenever a review is added, edited, or removed" with
zero risk of the stored value desyncing from the underlying reviews (no update-hook code to keep in
sync, no risk of drift if a review is removed via Django admin or a future bulk operation).
Aggregate queries here are cheap (project's "learning-project MVP scale" per constitution NFRs;
same reasoning 002/004 used to skip denormalization elsewhere) — no measured need to pre-compute.

**Alternatives considered**:
- Denormalized `Product.average_rating`/`Product.review_count` fields updated via `save()`
  overrides or signals — rejected: adds a second source of truth and signal-ordering complexity
  the on-read aggregate avoids entirely, for a scale where an `AVG`/`COUNT` aggregate is not a
  measurable bottleneck.

## 5. Vendor and Administrator feedback views — new endpoints vs. reuse

**Decision**: Two new read-only list endpoints — `GET /api/vendor/reviews` (scoped to the
requesting Vendor's own shops' products, queryset-filtered) and `GET /api/admin/reviews` (all
reviews, plus `DELETE /api/admin/reviews/{review_id}` for moderation) — mirroring the existing
`VendorProductListCreateView`/`AdminShopListView` precedent (queryset-level ownership filtering,
not object-level checks alone).

**Rationale**: Directly follows FR-007/FR-009 (Vendor sees only their own shop's reviews, queryset-
filtered) and FR-010/FR-011 (Administrator sees and can remove any review) using the exact
queryset-filtering pattern this codebase already established in `apps/catalog/views.py` (`Product.
objects.filter(shop__owner=self.request.user)`) and `apps/vendors`/`apps/orders`'s admin list
views, so no new authorization pattern is introduced.

**Alternatives considered**:
- Have the Vendor/Administrator reuse the public `CatalogProductDetailSerializer`'s embedded
  reviews by fetching each product individually — rejected: doesn't satisfy "view all reviews
  across their shop's products... in one place" (spec User Story 3/4); a dedicated list endpoint
  is the same shape as every other cross-product Vendor/Administrator view already in this
  codebase.

## 6. Moderation delete semantics

**Decision**: Administrator removal is a hard `DELETE` (row removed from the database), not a
soft-delete/hidden flag.

**Rationale**: Spec Assumptions explicitly rule out "a separate 'hidden but retained' moderation
state or an appeal workflow" for this feature. A hard delete is simpler (Constitution Principle
VI, YAGNI) and satisfies FR-011/FR-012/Edge-Cases ("treated as not having reviewed... able to
submit a new review") without extra state to reason about.

**Alternatives considered**:
- Soft-delete flag (`is_removed`) mirroring `catalog.Product`'s pattern — rejected: `Product`
  soft-deletes because a vendor's own listing history/audit value justifies keeping the row;
  spec Assumptions explicitly say this feature doesn't need moderation history or an appeal
  workflow, so the extra state has no consumer.

## 7. Testing approach

**Decision**: `pytest` + `pytest-django` + `factory_boy` (existing pattern) with a new
`ReviewFactory` in `tests/factories.py`, plus a new `OrderItemFactory` (does not yet exist —
004-order-fulfillment's tests built `OrderItem` rows via `place_order()`/`advance_order_item_status()`
service calls directly rather than a factory) needed here specifically to set up DELIVERED-status
fixtures quickly across many review-eligibility test cases. DRF `APIClient` for endpoint-level
contract tests (customer create/update/reject-ineligible, public read + aggregate, vendor scoping,
admin list + delete). Frontend covered by manual quickstart walkthroughs, matching 001-004's
approach (no frontend automated test suite exists in this repo).

**Rationale**: Consistent with every prior feature's testing setup; the new `OrderItemFactory` is
a small, reusable addition future features will likely also want (it was a gap 004 worked around
rather than filled).

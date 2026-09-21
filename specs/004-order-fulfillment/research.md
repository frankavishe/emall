# Phase 0 Research: Vendor Order Fulfillment

All items below were open decisions in the Technical Context, not `[NEEDS CLARIFICATION]` markers
in spec.md — the spec's Clarifications/Assumptions sections already fixed scope; this file fixes
the *how*.

## 1. Status transition enforcement lives in the service layer, not the model or serializer

**Decision**: A single function, `orders.services.advance_order_item_status(order_item, new_status,
actor)`, is the only path that changes `OrderItem.status`. It validates the requested transition
against a fixed adjacency map (`PENDING→PROCESSING`, `PROCESSING→SHIPPED`, `SHIPPED→DELIVERED`,
and `PENDING→CANCELLED`/`PROCESSING→CANCELLED`) before writing anything, raising a typed error
(mirroring `orders.services.CheckoutError`) for any other requested transition.

**Rationale**: `place_order()` already established the precedent of putting all order-mutation
correctness in `apps/orders/services.py`, callable from exactly one view, per the constitution's
Extensibility/Reusability guidance ("domain logic... belongs in model methods or service functions
callable from multiple entry points, not duplicated inline in view functions"). A service function
is easier to unit-test against the full transition matrix (FR-003, SC-002) than a serializer
`validate()` method, and keeps the view a thin HTTP-shape translator like `CheckoutView` already is.

**Alternatives considered**: `django-fsm` or a similar state-machine library — rejected, the
transition graph here is five edges on one field; the constitution's Simplicity principle (YAGNI)
argues against a new dependency for something a five-entry dict expresses directly. A `clean()`/
`save()` override on the model — rejected, `place_order()` sets the same field's initial value
(`PENDING`) via plain assignment inside its own transaction, so overloading `save()` with
transition logic would either not run in that path or would need a bypass flag, both worse than one
explicit service function every write path calls.

## 2. Stock restoration on cancellation: same atomic + `select_for_update()` pattern as checkout

**Decision**: When `advance_order_item_status()` transitions a line to `CANCELLED`, it opens a
`transaction.atomic()` block, takes a `select_for_update()` lock on the line's `Product` row,
increments `stock_quantity` by the cancelled `OrderItem.quantity`, writes the new `OrderItem.status`,
and appends the `OrderItemStatusEvent` row — all inside that one transaction.

**Rationale**: FR-011 requires stock restoration to happen atomically with the cancellation (no
partial state), and the constitution's Reliability NFR requires state-changing operations to be
transactional so a crash mid-operation can't decrement... er, leave inconsistent state. Locking the
`Product` row with `select_for_update()` mirrors `place_order()`'s existing race-avoidance pattern
exactly (research.md §4 of 003-cart-checkout) — a Vendor cancelling a line concurrently with an
unrelated checkout touching the same product must not lose or double-count the restored quantity.

**Alternatives considered**: A Django signal (`post_save` on `OrderItem`) that restores stock when
`status` becomes `CANCELLED` — rejected, signals make the atomicity boundary implicit and harder to
reason about (would the signal fire inside the same transaction as the status write, or after
commit?); an explicit call inside the same service function keeps the whole operation in one
visible, testable transaction block, consistent with `place_order()`.

## 3. Fulfillment history: a new minimal append-only table, not JSON on `OrderItem`

**Decision**: A new model, `OrderItemStatusEvent` (`order_item` FK, `status`, `changed_at
auto_now_add=True`), gets one row per status change, created by `advance_order_item_status()` in
the same transaction as the status write. No `updated_by`/actor field is stored, since the actor is
always the line's owning Vendor by construction (FR-003/FR-004) and the spec doesn't call for
recording *who* beyond that.

**Rationale**: FR-009 requires a queryable history "so a stalled or disputed line can be
investigated after the fact" — a real relational table supports ordering/filtering by an
Administrator's oversight view (User Story 3) far more naturally than a JSON blob column would, and
matches how every other auditable-state feature in this codebase (Shop's `status_changed_at`,
`EmailVerificationToken`/`PasswordResetToken`) already prefers explicit columns/rows over opaque
blobs.

**Alternatives considered**: Reuse `Shop`'s pattern of a single `status_changed_at` timestamp
column directly on `OrderItem` (no separate table) — rejected, that only records the *most recent*
change, not the full history FR-009 explicitly asks for (a line that went
PENDING→PROCESSING→CANCELLED needs all three timestamps visible to an Administrator investigating
it, not just the last one).

## 4. Vendor/Administrator visibility split lives in the serializer choice per view, not one shared serializer

**Decision**: `VendorOrderItemSerializer` (current status only) and `AdminOrderItemSerializer`
(current status + nested `OrderItemStatusEvent` history + shop/vendor identity) are two distinct
serializer classes over the same `OrderItem` model, selected by which view is serving the request.
The existing Customer-facing `OrderItemSerializer` (003-cart-checkout) is untouched.

**Rationale**: The clarification session fixed history visibility as Administrator-only — the
simplest way to guarantee a Vendor's fulfillment list response can never leak history is for that
serializer to simply not declare the field, rather than a shared serializer with a conditional
`to_representation()` branch keyed on `request.user.role` (easy to get backwards, harder to unit
test that the branch is actually reached in every call site).

**Alternatives considered**: One `OrderItemSerializer` with a `SerializerMethodField` for history
that returns `None`/omits based on `self.context["request"].user.role` — rejected as the kind of
conditional-shape serializer the constitution's Simplicity principle argues against when two
already-distinct call sites (Vendor list view, Admin oversight view) make separate serializer
classes just as simple and impossible to misconfigure across roles.

## 5. Vendor ownership enforcement: queryset filtering for list, object permission for the mutating action

**Decision**: `VendorOrderItemListView.get_queryset()` filters to
`OrderItem.objects.filter(product__shop__owner=request.user)` (list — many rows, no single-object
identity to hide). `VendorOrderItemStatusUpdateView` additionally applies a new
`apps.orders.permissions.IsOrderItemShopOwner` object permission (`obj.product.shop.owner_id ==
request.user.id` and, for the APPROVED-only mutation gate, `obj.product.shop.status ==
Shop.Status.APPROVED`) on the single line item being updated, returning 404 for another vendor's
line ID (FR-004's "MUST NOT reveal that line item's details").

**Rationale**: Directly reuses 003-cart-checkout's research.md §6 precedent (queryset-level
filtering for a user's own list of rows) combined with `apps.catalog.permissions
.IsApprovedShopOwnerForProduct`'s precedent (object-level check requiring APPROVED specifically for
a mutating action, vs. a looser ownership-only check for read/list). No new pattern invented — this
feature composes two already-reviewed patterns rather than adding a third.

**Alternatives considered**: A single object-permission class applied to both list and detail views
— rejected, DRF's `has_permission` runs before the queryset exists for a list view, so it cannot
express "only this vendor's rows" for a list the way `get_queryset()` filtering does; the codebase
already treats these as two different tools for two different shapes of endpoint (see
`OrderListView` vs `OrderDetailView` in 003-cart-checkout).

## 6. Endpoint routing: `orders` app grows `vendor_urlpatterns`/`admin_urlpatterns`, no new app

**Decision**: `apps/orders/urls.py` adds two more urlpattern lists alongside its existing default
and `checkout_urlpatterns`: `vendor_urlpatterns` (`GET /api/vendor/order-items`,
`PATCH /api/vendor/order-items/<id>/status`) and `admin_urlpatterns` (`GET
/api/admin/order-items`), included in `config/urls.py` at the existing `api/vendor/` and
`api/admin/` prefixes alongside `apps.vendors.urls`/`apps.catalog.urls`'s own vendor/admin lists.

**Rationale**: Directly reuses the exact multi-urlpatterns-per-app convention `apps/catalog/urls.py`
and `apps/vendors/urls.py` already established (a default list plus role-prefixed lists exported
and included separately) — 003-cart-checkout's research.md §7/§8 already chose not to invent a
fourth app (`fulfillment`) for a state field that lives on an existing model, and that reasoning
applies again here even more directly, since `OrderItem` itself already lives in `apps/orders`.
`PATCH .../status` (not a bare `PATCH` on the order item resource) makes the single mutable concern
explicit in the URL, since no other `OrderItem` field is ever updated by this feature.

**Alternatives considered**: A new `apps/fulfillment` app — rejected per the constitution's
Maintainability section, which names the fixed app list (`accounts, vendors, catalog, cart, orders,
payments, feedback, core`) with no `fulfillment` entry; fulfillment status is order-line data, not
a separate bounded concept, and 003-cart-checkout's plan already anticipated this by putting
`OrderItem.status` in `orders` from the start.

## 7. Customer-facing visibility requires no new work

**Decision**: No change to `OrderItemSerializer`, `OrderDetailView`, or
`frontend/src/app/orders/[id]/page.tsx`. `OrderItemSerializer` already includes `status`
(003-cart-checkout) and the page already renders `item.status` per line. Widening
`OrderItem.Status`'s choices is sufficient for the existing field to start showing the new values.

**Rationale**: Verified by reading both files directly rather than assuming — `OrderItemSerializer.
Meta.fields` already lists `"status"` and the page template already interpolates `item.status`
(spec.md Summary). Building a second Customer-facing status display would duplicate an already-
correct one for no behavioral gain (Constitution Principle VI, Simplicity).

**Alternatives considered**: None seriously considered — this is a verification, not a design
choice; the alternative (rebuild the field) was rejected purely because inspection showed it
already exists and already works, which User Story 2's Independent Test (re-run against the
existing page) will confirm end to end in the implementation phase.

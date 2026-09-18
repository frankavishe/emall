# Phase 0 Research: Shopping Cart & Checkout

All items below were open decisions in the Technical Context, not `[NEEDS CLARIFICATION]` markers
in spec.md — the spec's Assumptions section already fixed scope; this file fixes the *how*.

## 1. Cart model shape and creation timing

**Decision**: `Cart` is a `OneToOneField` to `User` (not a standalone keyed-by-token model), created
lazily via `get_or_create` the first time a Customer's cart is accessed (view a cart, add an item)
rather than at registration/login time.

**Rationale**: Spec Assumptions restrict carts to logged-in Customers only (no guest cart), so a
1:1 relationship is the simplest model that satisfies FR-006 (per-account persistence) — no cart
token, no session cart to merge on login. Lazy creation avoids touching the 001-accounts-auth
registration flow from this feature (Constitution Principle VI — simplicity; don't modify a
finished feature's write path to serve a new one).

**Alternatives considered**: Create a `Cart` row at registration time (in `accounts` signal/hook) —
rejected, couples this feature's schema into a prior feature's completed flow for no behavioral
gain, since `get_or_create` on first cart access is equally correct and self-contained within the
new `cart` app.

## 2. Cart line pricing: live-read, never frozen

**Decision**: `CartItem` stores only `product` (FK) and `quantity` — no `unit_price` column. Every
read (cart view, checkout re-validation) computes price and availability from the *current*
`Product` row via serializer method fields / service logic, not a stored snapshot.

**Rationale**: User Story 3 and spec Assumptions are explicit that cart prices are never frozen —
only `OrderItem.unit_price` freezes at the moment an `Order` is actually created (FR-012,
Assumptions). Storing a price on `CartItem` would require an extra sync step to keep it live and
creates a second source of truth that could drift from `Product.price`.

**Alternatives considered**: Snapshot price on add-to-cart, refreshed on every view — rejected,
adds a write on every cart read for no benefit over just reading `Product.price` directly, and
risks a missed-refresh path showing stale data (the exact bug User Story 3 exists to prevent).

## 3. Duplicate-add merges into one line

**Decision**: `CartItem` has a `unique_together = ("cart", "product")` constraint. Adding a product
already in the cart increments the existing row's `quantity` (inside a single `get_or_create` +
conditional update) rather than the view layer having to search for and merge duplicate lines.

**Rationale**: FR-005 requires "the existing line's quantity increases rather than creating a
second line" — encoding this as a DB constraint makes it impossible to violate accidentally from
any future call site, not just the one view built in this feature.

**Alternatives considered**: Allow multiple rows per `(cart, product)` and merge them at
serialization time — rejected, pushes correctness into every read path instead of enforcing it once
at the write boundary; also complicates the "increase or decrease quantity" and "remove a line"
UX from User Story 1, which assume one row per product.

## 4. Checkout atomicity and the oversell race

**Decision**: `orders.services.place_order()` wraps the entire checkout — line re-validation,
payment call, `Order`/`OrderItem` creation, stock decrement, cart clear — in one
`transaction.atomic()` block. Before re-validating, it takes `select_for_update()` locks on the
touched `Product` rows, always acquired in a fixed order (ascending `product_id`) to avoid
deadlocking against another concurrent checkout that shares a product.

**Rationale**: FR-014 requires stock decrement and Order creation to be all-or-nothing; the Edge
Cases section requires that of two concurrent checkouts that would together oversell a product,
only the ones that fit within available stock succeed, with no partial order. Row-level locking
inside one transaction is the standard, minimal-dependency way to close this race in PostgreSQL —
no new dependency, no application-level lock/queue needed at this scale.

**Alternatives considered**: Optimistic concurrency (a `version` column, retry on conflict) —
rejected as unnecessary complexity for MVP scale (Constitution Principle VI); pessimistic
row-locking is simpler to reason about and sufficient at the stated scope. Locking the whole `Cart`
row instead of individual `Product` rows — rejected, doesn't prevent the cross-cart oversell race
the Edge Case actually describes (two *different* Customers' carts touching the same product).

## 5. Payment: swappable mock service

**Decision**: `apps/payments/services.py` defines `PaymentService` (ABC, one `charge(*, amount,
method) -> PaymentResult` method) and `MockPaymentService`, retrieved via a `get_payment_service()`
factory — mirroring `apps/core/email.py`'s `EmailService` / `DjangoEmailService` /
`get_email_service()` pattern exactly. `charge()` takes only an opaque `method` label string (e.g.
`"card"`), never card fields. `MockPaymentService` succeeds for any method value except the
case-insensitive sentinel `"declined"`, which deterministically fails — giving FR-016's failure
path something concrete and repeatable to test against without a real gateway.

**Rationale**: Constitution Principle IV requires mocked edges to be a real, swappable service
interface, not inlined fake branches in checkout business logic — reusing the exact shape already
reviewed for `EmailService` keeps this consistent across the codebase. The sentinel-value failure
trigger is the simplest way to deterministically exercise FR-016/Acceptance Scenario 5 without
adding test-only branching inside `place_order()` itself.

**Alternatives considered**: A `success: bool` parameter threaded through the checkout API request
— rejected, that's a test hook leaking into the public contract; a magic method value is
self-contained inside the mock and disappears entirely when a real gateway is swapped in.

## 6. Ownership enforcement: queryset filtering, not object permissions

**Decision**: `Cart`, `Order` access is scoped by filtering every queryset to `customer=request.user`
(or `cart__customer=request.user` for `CartItem`) inside the view's `get_queryset()`/lookup, not
via a `has_object_permission` check on an otherwise-unscoped queryset. `GET /api/orders/{id}/` for
another Customer's order 404s (not 403) — the row is simply not in the requester's queryset — the
same uniform-not-found shape 002-product-catalog already uses for hidden products.

**Rationale**: The constitution's Security & Non-Functional Requirements section requires
list/detail endpoints returning another user's data to filter by ownership "at the queryset level,
not only in serializers." Filtering at the queryset level also satisfies FR-021 (deny access to
another Customer's order) for free — there's no separate object-permission class to keep in sync
with the queryset filter, one less place this could drift.

**Alternatives considered**: An object-level permission class checking `obj.customer == request.
user` on an unfiltered queryset (mirroring `IsProductOwner`) — rejected here specifically because
that pattern is for *Vendor* ownership across many shops where a 403 is informative; for a
Customer's own private data, a uniform 404 is the safer default (doesn't confirm another Customer's
order ID even exists) and queryset filtering gets both correctness and that shape in one place.

## 7. New app boundaries: `cart`, `orders`, `payments`

**Decision**: Three new Django apps — `apps/cart`, `apps/orders`, `apps/payments` — created now,
matching the exact names already reserved as future placeholders in 002-product-catalog's plan
Project Structure. `PaymentRecord` lives in `payments`, not nested inside `orders`, even though it
has no endpoints of its own in this feature.

**Rationale**: Constitution's Maintainability section names these as established app boundaries;
following the reservation avoids a later rename/move. Keeping `payments` separate from `orders` — a
thin app for now — mirrors the constitution's "swappable service interface" framing for Principle
IV: the payment concern is conceptually independent of order bookkeeping even though today it's
only invoked from inside `place_order()`.

**Alternatives considered**: Fold `PaymentRecord`/`PaymentService` into `apps/orders` since nothing
outside checkout touches them yet — rejected, contradicts the app boundaries the prior feature's
plan already committed to, and a future payments-specific concern (refunds, a real gateway webhook
receiver) would then require a disruptive extraction later.

## 8. Checkout endpoint placement

**Decision**: `apps/orders/urls.py` exposes two urlpattern lists — a default list (`orders/`,
`orders/<id>/`) included at `/api/orders/`, and a separate `checkout_urlpatterns` (`checkout/`)
included directly at `/api/` in `config/urls.py` — giving `POST /api/checkout/`,
`GET /api/orders/`, `GET /api/orders/{id}/`.

**Rationale**: Reuses the exact dual-urlpatterns-per-app pattern `apps/catalog/urls.py` already
established (`vendor_urlpatterns` included at one prefix, default `urlpatterns` at another) rather
than inventing a new routing convention. `POST /api/checkout/` as its own top-level action (not
`/api/orders/checkout/`) matches how the action reads to a client — it's the single verb that turns
a cart into an order, not a sub-resource of order history.

**Alternatives considered**: `POST /api/orders/` (checkout as "create an order") — rejected, the
request body for checkout (shipping details, payment method) doesn't resemble an `Order`
representation at all, and overloading the list-endpoint's `POST` verb for a fundamentally
different, multi-step operation (re-validation + payment + stock mutation) is less clear than a
dedicated action endpoint.

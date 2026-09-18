# Phase 1 Data Model: Shopping Cart & Checkout

Source: `spec.md` Key Entities, Functional Requirements FR-001–FR-022. All fields live in
PostgreSQL (Constitution Principle IV: schema is "real core", never mocked).

## Cart (`apps/cart/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `customer` | `OneToOneField(User, related_name="cart")`, `on_delete=CASCADE` | Exactly one active cart per Customer account (spec Key Entities); created lazily via `get_or_create` (research.md §1), never at registration time |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `updated_at` | `DateTimeField(auto_now=True)` | |

**Validation rules**: Only a `User` with `role == CUSTOMER` may have a `Cart` created for them
(enforced at the view layer via `IsCustomer`, FR-022) — not a DB constraint, consistent with how
role checks are enforced elsewhere in this codebase.

**Computed, not stored**: `total` — sum of each *available* line's subtotal (see CartItem below).
Never persisted, always computed at read time from live `Product` data (research.md §2, User
Story 3).

**Relationships**: One `User` (Customer) → one `Cart`. One `Cart` → many `CartItem`.

## CartItem (`apps/cart/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `cart` | `ForeignKey(Cart, related_name="items")`, `on_delete=CASCADE` | |
| `product` | `ForeignKey(Product, related_name="cart_items")`, `on_delete=CASCADE` | From `apps.catalog` (002-product-catalog), referenced not redefined |
| `quantity` | `PositiveIntegerField` | `MinValueValidator(1)` at the serializer layer (FR-001 "at least 1") — `PositiveIntegerField` alone allows `0`, which is not a valid cart line |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `updated_at` | `DateTimeField(auto_now=True)` | |

**Validation rules**:
- `(cart_id, product_id)` unique together — FR-005, research.md §3. Adding an already-present
  product increments this row's `quantity` instead of inserting a second row.
- `quantity` cannot be set (on add or update) above the product's *current* `stock_quantity` —
  FR-007, re-checked against live `Product` data on every add/update request, not just at
  creation.
- No `unit_price` field — price is always read live from `product.price` at view/checkout time
  (research.md §2), never frozen on the line.

**Computed, not stored** (serializer method fields, read live from `product` each time):
- `unit_price` — `product.price`.
- `subtotal` — `product.price * quantity`.
- `is_available` — `product.is_published AND NOT product.is_deleted AND product.shop.status ==
  APPROVED AND quantity <= product.stock_quantity` (User Story 3, Edge Cases — an un-approved
  shop's listings behave like unpublished ones). An unavailable line is still returned in the cart
  response (so the Customer can see and resolve it) but excluded from `Cart.total` and blocks
  checkout (FR-008, User Story 3 Scenario 3) until removed or adjusted.

**Relationships**: One `Cart` → many `CartItem`. One `Product` (from `apps.catalog`) → many
`CartItem` (across different Customers' carts).

## Order (`apps/orders/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `customer` | `ForeignKey(User, related_name="orders")`, `on_delete=CASCADE` | Ownership anchor for every access-control check (FR-018, FR-021, research.md §6) |
| `status` | `CharField`, `choices=Order.Status` | `Status.PLACED` only, set at creation and never changed by this feature (FR-012 requires the field to exist; no cancellation/refund flow is in scope per spec Assumptions) |
| `recipient_name` | `CharField` | Shipping details, FR-009 |
| `address_line` | `CharField` | Shipping details, FR-009 |
| `city` | `CharField` | Shipping details, FR-009 |
| `region` | `CharField` | Shipping details, FR-009 (state/region) |
| `postal_code` | `CharField` | Shipping details, FR-009 |
| `country` | `CharField` | Shipping details, FR-009 |
| `phone` | `CharField` | Shipping details, FR-009 (contact phone number) |
| `placed_at` | `DateTimeField(auto_now_add=True)` | FR-012 "placed-at timestamp"; also the sort key for order history (FR-020, most recent first) |

**Validation rules**: All shipping fields required and non-blank (FR-009, FR-010) — enforced at
the serializer layer with field-level error messages naming which field failed. An `Order` is only
ever created by `orders.services.place_order()` inside the atomic checkout transaction
(research.md §4) — never via a generic `POST` that accepts arbitrary `status`/`placed_at`.

**Computed, not stored**: `total` — sum of `OrderItem.subtotal` across all its items. Safe to
compute on read (never mutated after creation) rather than denormalized, since every `OrderItem.
unit_price` is already frozen.

**Relationships**: One `User` (Customer) → many `Order`. One `Order` → many `OrderItem`. One
`Order` → one `PaymentRecord` (from `apps.payments`).

## OrderItem (`apps/orders/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `order` | `ForeignKey(Order, related_name="items")`, `on_delete=CASCADE` | |
| `product` | `ForeignKey(Product, related_name="order_items", on_delete=PROTECT)` | `PROTECT`, not `CASCADE` — a `Product` row backing a historical order line must never be removable out from under it (catalog already soft-deletes, so this is a structural guarantee, not a workaround) |
| `quantity` | `PositiveIntegerField` | The ordered amount, captured at purchase (FR-012) |
| `unit_price` | `DecimalField(max_digits=10, decimal_places=2)` | Frozen at the moment the `Order` is created (FR-012, spec Assumptions) — independent of any later change to `product.price` |
| `status` | `CharField`, `choices=OrderItem.Status` | `Status.PENDING` only, set at creation (Constitution Principle VI — the field must exist because one `Order` can span multiple vendors' shops, FR-013). No endpoint in this feature mutates it; vendor-side fulfillment management is out of scope per spec Assumptions |

**Validation rules**: `quantity` and stock availability were already verified against `product.
stock_quantity` inside the locked checkout transaction before this row is created (research.md
§4) — no further validation needed at the row level itself. Every `OrderItem` created inside one
`place_order()` call belongs to the same `Order`, even when the underlying products span multiple
different `Shop`s (FR-013) — the vendor a given line belongs to is reached via
`order_item.product.shop`, with no separate denormalized `shop` FK (Constitution Principle VI —
simplicity; `product.shop` is already stable, products are never reassigned to a different shop).

**Computed, not stored**: `subtotal` — `unit_price * quantity`.

**Relationships**: One `Order` → many `OrderItem`. One `Product` → many `OrderItem` (across
different orders, protected from deletion while referenced).

## PaymentRecord (`apps/payments/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `order` | `OneToOneField(Order, related_name="payment", on_delete=CASCADE)` | Only ever created alongside a successfully created `Order`, in the same atomic transaction (research.md §5) — a failed mock payment attempt produces no row anywhere, since there is no `Order` for it to attach to |
| `method` | `CharField(max_length=50)` | An opaque label only (e.g. `"card"`) — never raw card number/CVV, per Constitution Principle III |
| `status` | `CharField`, `choices=PaymentRecord.Status` | `Status.SUCCEEDED` only — the only status a persisted row can ever have, since a failed attempt never reaches row creation (FR-016) |
| `transaction_reference` | `CharField(max_length=64, unique=True)` | Opaque mock reference (a generated UUID string), not tied to any real payment network |
| `created_at` | `DateTimeField(auto_now_add=True)` | |

**Validation rules**: Never persists card numbers, CVV/CVC, or any other raw payment instrument
data — the mock `PaymentService.charge()` (research.md §5) doesn't even accept such fields as
input, so there is nothing sensitive to accidentally store (Constitution Principle III).

**Relationships**: One `Order` → one `PaymentRecord`.

## State machines

**Order.status** (single reachable value in this feature — see Order table above):

```
(checkout succeeds inside place_order())
              │
              ▼
          PLACED
```

No transitions out of `PLACED` are implemented by this feature (cancellation/refund is explicitly
out of scope, spec Assumptions) — the field exists now so a future feature can add transitions
without a schema migration on `Order` itself.

**OrderItem.status** (single reachable value in this feature — see OrderItem table above):

```
(OrderItem created as part of place_order())
              │
              ▼
          PENDING
```

Per-line, independent of every other line in the same `Order` (FR-013) — a future vendor
fulfillment feature transitions each vendor's own lines independently without touching lines
belonging to other vendors' shops in the same order.

## Not modeled in this feature

- **Shipping cost, tax, promo/discount codes, saved addresses, order cancellation/refunds,
  vendor-side fulfillment status updates** — all explicitly out of scope per spec Assumptions;
  `Order`/`OrderItem` carry the fields (`status`, shipping columns) a future feature needs without
  requiring a schema migration to add them, but no logic to compute or mutate them beyond `PLACED`/
  `PENDING` is built here.

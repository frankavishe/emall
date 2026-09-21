# Phase 1 Data Model: Vendor Order Fulfillment

Source: `spec.md` Key Entities, Clarifications, Functional Requirements FR-001–FR-011. Both
entities live in PostgreSQL (Constitution Principle IV: schema is "real core", never mocked).

## OrderItem (`apps/orders/models.py`, existing model — extended)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | existing, unchanged |
| `order` | `ForeignKey(Order, related_name="items")`, `on_delete=CASCADE` | existing, unchanged |
| `product` | `ForeignKey(Product, related_name="order_items", on_delete=PROTECT)` | existing, unchanged |
| `quantity` | `PositiveIntegerField` | existing, unchanged; the amount restored to `product.stock_quantity` if this line is cancelled (FR-011) |
| `unit_price` | `DecimalField(max_digits=10, decimal_places=2)` | existing, unchanged |
| `status` | `CharField`, `choices=OrderItem.Status` | **CHANGED**: `Status` widened from `{PENDING}` to `{PENDING, PROCESSING, SHIPPED, DELIVERED, CANCELLED}` (FR-002). Default remains `PENDING`, set at creation by `place_order()` (003-cart-checkout, unchanged) |

**Validation rules** (new, this feature):
- Only `orders.services.advance_order_item_status()` may change `status` — no view or serializer
  writes this field directly (research.md §1).
- A transition is valid only if it matches the fixed adjacency map: `PENDING→PROCESSING`,
  `PROCESSING→SHIPPED`, `SHIPPED→DELIVERED`, `PENDING→CANCELLED`, `PROCESSING→CANCELLED` (FR-002,
  FR-003). Any other requested `(current, requested)` pair — backward, skipped, from a terminal
  state (`DELIVERED`/`CANCELLED`), or `SHIPPED→CANCELLED` — is rejected with no write (FR-003,
  Edge Cases, SC-002).
- The acting Vendor must own the shop the line's `product` belongs to, and that shop must be
  `APPROVED` at the moment of the request (FR-004, FR-010) — checked by
  `apps.orders.permissions.IsOrderItemShopOwner` before `advance_order_item_status()` is called.

**Side effect on `CANCELLED`**: `product.stock_quantity` is incremented by `quantity`, inside the
same transaction as the status write (FR-011, research.md §2).

**Relationships**: unchanged from 003-cart-checkout — one `Order` → many `OrderItem`; one `Product`
→ many `OrderItem`. New: one `OrderItem` → many `OrderItemStatusEvent`.

## OrderItemStatusEvent (`apps/orders/models.py`, new model)

| Field | Type | Notes |
|---|---|---|
| `id` | BigAutoField (PK) | |
| `order_item` | `ForeignKey(OrderItem, related_name="status_events", on_delete=CASCADE)` | The line this event records a change for |
| `status` | `CharField`, `choices=OrderItem.Status` | The status the line moved *to* at this event (FR-009) |
| `changed_at` | `DateTimeField(auto_now_add=True)` | When this change was recorded; the ordering key for history display |

**Validation rules**: Created only by `advance_order_item_status()`, in the same transaction as the
`OrderItem.status` write it records (research.md §3) — never created or mutated independently.
Append-only: rows are never updated or deleted once created.

**Visibility**: Returned only by the Administrator oversight endpoint
(`AdminOrderItemSerializer`); never included in the Vendor fulfillment list/update response or the
Customer-facing order detail response (Clarifications session 2026-09-21, research.md §4).

**Relationships**: One `OrderItem` → many `OrderItemStatusEvent`, ordered by `changed_at` ascending
for display (oldest transition first).

## State machine

**OrderItem.status** (extends the single-value diagram from 003-cart-checkout's data-model.md):

```
                    (place_order() creates the line)
                                  │
                                  ▼
                              PENDING ──────────────┐
                                  │                  │
                        (Vendor advances)   (Vendor cancels,
                                  │           stock restored)
                                  ▼                  │
                            PROCESSING ───────────────┤
                                  │                  │
                        (Vendor advances)   (Vendor cancels,
                                  │           stock restored)
                                  ▼                  ▼
                              SHIPPED            CANCELLED
                                  │              (terminal)
                        (Vendor advances)
                                  │
                                  ▼
                              DELIVERED
                              (terminal)
```

Per-line, independent of every other line in the same `Order` (FR-013 from 003-cart-checkout,
reaffirmed by this feature's FR-004/Acceptance Scenario 4) — one Vendor advancing or cancelling
their line never touches another vendor's line on the same `Order`. No transition skips a level or
moves backward (FR-003); `SHIPPED` and later have no path to `CANCELLED` (spec Assumptions — an
in-transit shipment is a return/refund scenario, out of scope).

## Not modeled in this feature

- **Returns/refunds after `SHIPPED`, notification delivery on status change, bulk/batch status
  updates, payment/refund record changes on cancellation** — all explicitly out of scope per spec
  Assumptions; `OrderItemStatusEvent` gives a future feature a ready-made history to build
  notifications or dispute tooling on top of, without a schema migration to add it later.

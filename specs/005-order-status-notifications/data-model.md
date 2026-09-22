# Data Model: Order Status Notifications

## Summary

This feature introduces **no new database table and no schema changes**. It is a read-only
consumer of existing entities, triggered as a side effect of an existing write path
(`advance_order_item_status()`). Per the spec's Assumptions, no notification-delivery audit log is
required — the authoritative record of *what happened* remains 004-order-fulfillment's existing
`OrderItemStatusEvent` table; this feature only adds *what the Customer was told about it*, which is
not persisted.

## Entities read (all pre-existing, unmodified)

### `Order` (from 003-cart-checkout)
- `customer` (FK → `User`) — resolves the notification recipient via `order_item.order.customer`.

### `OrderItem` (from 003-cart-checkout, extended by 004-order-fulfillment)
- `order` (FK → `Order`)
- `product` (FK → `Product`) — supplies the product name for the notification body.
- `status` — the new value this feature reports on (`PROCESSING` / `SHIPPED` / `DELIVERED` /
  `CANCELLED`).

### `User` (from 001-accounts-auth)
- `email` — the notification's recipient address.
- `is_email_verified` — read only to confirm it is *not* used as a gate (spec Assumptions);
  notifications send regardless of its value.

## Conceptual entity (not persisted)

### Notification
Represents one email sent as a side effect of one successful `OrderItem` status transition.
Not modeled as a database row — it exists only as the arguments to
`EmailService.send_order_item_status_email(order_item)` at the moment it is sent, mirroring how
001-accounts-auth's verification/reset emails are also not logged to a table of their own.

| Field (conceptual) | Source |
|---|---|
| Recipient | `order_item.order.customer.email` |
| Order reference | `order_item.order_id` |
| Item reference | `order_item.product.name` |
| New status | `order_item.status` (at time of send — always the post-transition value) |

## State transitions

No new state machine. This feature observes, but does not add to or modify, the existing
`OrderItem.Status` adjacency rules already enforced by `advance_order_item_status()`
(`apps/orders/services.py`, unchanged by this feature):

```text
PENDING → PROCESSING → SHIPPED → DELIVERED
PENDING → CANCELLED
PROCESSING → CANCELLED
```

A notification is sent for the four non-`PENDING` states above (`PENDING` is the initial state set
by `place_order()`, not a transition target, so it has nothing to notify about — consistent with
FR-001 only naming PROCESSING/SHIPPED/DELIVERED/CANCELLED).

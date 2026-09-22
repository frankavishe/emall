# Contract: Order Status Notification Email

This feature adds no new HTTP endpoint and changes no existing request/response shape —
`PATCH /api/vendor/order-items/{id}/status/` (004-order-fulfillment's contract) is unchanged. The
externally observable interface this feature adds is the **email sent to the Customer** as a side
effect of that endpoint's existing, successful call to `advance_order_item_status()`
(research.md §1). Traceability: each row below references the FR(s) it satisfies.

## Trigger

Fires once, after commit, for every successful `OrderItem` status transition to `PROCESSING`,
`SHIPPED`, `DELIVERED`, or `CANCELLED` (FR-001, FR-004). Does not fire for a rejected/invalid
transition attempt (FR-003) or for the initial `PENDING` state set at checkout.

## Recipient

`order_item.order.customer.email` — always, regardless of `is_email_verified` (FR-006).

## `EmailService.send_order_item_status_email(order_item)`

New method on the existing `apps.core.email.EmailService` abstract class and its
`DjangoEmailService` implementation (FR-007), called from
`apps.orders.services.advance_order_item_status()` via `transaction.on_commit()` (research.md §1).

### Message content by status

| `order_item.status` | Subject | Body states |
|---|---|---|
| `PROCESSING` | `Your order is being prepared` | Order id, product name, "being prepared" |
| `SHIPPED` | `Your order has shipped` | Order id, product name, "has shipped" |
| `DELIVERED` | `Your order has been delivered` | Order id, product name, "has been delivered" |
| `CANCELLED` | `An item in your order was cancelled` | Order id, product name, "was cancelled"; no mention of refund/payment status (FR-008) |

Every variant identifies the specific order (`order_item.order_id`) and the specific line item's
product (`order_item.product.name`) — never a whole-order summary (FR-002, spec Acceptance
Scenario 3).

### Failure isolation

A delivery exception raised by the underlying transport is caught and logged at the call site
(research.md §2) — it propagates neither back into the (already-committed) status transition nor
into the HTTP response of `PATCH /api/vendor/order-items/{id}/status/`, which still returns its
normal `200` (FR-005, SC-004).

## Non-goals (explicitly out of scope, per spec)

- No new/changed HTTP request or response shape on any endpoint.
- No SMS/push transport, no in-app/websocket notification, no notification-preferences or opt-out
  API (FR-009).
- No persisted notification/audit record (data-model.md) — delivery success/failure is not queryable
  after the fact via any API.

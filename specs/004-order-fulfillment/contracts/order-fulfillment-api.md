# API Contract: Vendor Order Fulfillment

Base paths: `/api/vendor/order-items/` (Vendor fulfillment queue), `/api/admin/order-items/`
(Administrator oversight). All bodies JSON. Traceability: each endpoint references the FR(s) it
satisfies. (No change to `/api/orders/{id}/` — its existing `items[].status` response field,
documented in 003-cart-checkout's contract, now reflects the wider `OrderItem.Status` set FR-002
defines; see research.md §7.)

## Vendor fulfillment queue (`/api/vendor/order-items/`)

All endpoints require `Authorization: Bearer <access_token>` and `role == VENDOR`, enforced by
`apps.core.permissions.IsVendor`, plus queryset-level filtering to the requester's own shops
(data-model.md, research.md §5).

### `GET /api/vendor/order-items/`
Satisfies FR-001. Lists order line items whose product belongs to one of the authenticated
Vendor's own shops, across every Customer's orders, paginated.

Response `200`:
```json
{
  "count": 2, "next": null, "previous": null,
  "results": [
    { "id": 100, "order_id": 42, "product": { "id": 5, "name": "USB-C Cable" },
      "quantity": 2, "unit_price": "9.99", "status": "PENDING",
      "shipping": { "recipient_name": "Ama Owusu", "address_line": "12 Ring Road",
        "city": "Accra", "region": "Greater Accra", "postal_code": "GA-184-9021",
        "country": "Ghana", "phone": "+233201234567" } }
  ]
}
```
`shipping` is included (denormalized from the parent `Order`) so a Vendor has what they need to
fulfill the line without a second request (Acceptance Scenario 1). No line belonging to another
vendor's shop ever appears (FR-001, FR-004).

### `PATCH /api/vendor/order-items/{id}/status/`
Satisfies FR-002, FR-003, FR-004, FR-010, FR-011. Request: `{ "status": "PROCESSING" }` (one of
`PROCESSING`, `SHIPPED`, `DELIVERED`, `CANCELLED`).

Calls `orders.services.advance_order_item_status()` (research.md §1) after
`apps.orders.permissions.IsOrderItemShopOwner` confirms the line's product belongs to a shop the
requester owns; a mutating request additionally requires that shop to be `APPROVED` (FR-010).

Response `200`: the updated line, same shape as a list row.

Errors:
- `404` — the line doesn't exist, or belongs to another vendor's shop (FR-004: indistinguishable
  from nonexistent, no detail leaked).
- `400` `{ "status": ["Cannot move PENDING to DELIVERED."] }` — requested transition isn't the
  single valid next step or a valid cancellation (FR-003, Edge Cases); stored status unchanged
  (SC-002).
- `400` `{ "status": ["This line is already CANCELLED."] }` (or `DELIVERED`) — attempted change
  from a terminal state.
- `403` — the line's shop is not currently `APPROVED` (FR-010).

On a `CANCELLED` transition, `product.stock_quantity` is incremented by the line's `quantity` in
the same transaction as the status write (FR-011) — not reflected in this endpoint's response body
directly, but visible on the product's own catalog endpoints immediately after.

## Administrator oversight (`/api/admin/order-items/`)

Requires `Authorization: Bearer <access_token>` and `role == ADMINISTRATOR`
(`apps.core.permissions.IsAdministrator`). Read-only — no mutating endpoint exists here (FR-008).

### `GET /api/admin/order-items/`
Satisfies FR-007, FR-009. Lists order line items across every shop/vendor, paginated, each
including its full status-change history.

Response `200`:
```json
{
  "count": 1, "next": null, "previous": null,
  "results": [
    { "id": 100, "order_id": 42, "product": { "id": 5, "name": "USB-C Cable" },
      "shop": { "id": 3, "name": "Kofi's Electronics" }, "quantity": 2, "unit_price": "9.99",
      "status": "PROCESSING",
      "status_history": [
        { "status": "PENDING", "changed_at": "2026-09-21T09:00:00Z" },
        { "status": "PROCESSING", "changed_at": "2026-09-21T10:30:00Z" }
      ] }
  ]
}
```
`status_history` (from `OrderItemStatusEvent`, data-model.md) is returned only on this endpoint —
never on the Vendor fulfillment list/update response or the Customer's order detail response
(Clarifications session 2026-09-21, research.md §4).

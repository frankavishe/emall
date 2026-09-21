# API Contract: Shopping Cart & Checkout

Base paths: `/api/cart/` (cart management), `/api/checkout/` (checkout action), `/api/orders/`
(order history). All bodies JSON. All endpoints require `Authorization: Bearer <access_token>` and
`role == CUSTOMER` (FR-022) — enforced server-side by `apps.core.permissions.IsCustomer`, plus
queryset-level filtering to `request.user` (data-model.md, research.md §6). Traceability: each
endpoint references the FR(s) it satisfies.

## Cart (`/api/cart/`)

### `GET /api/cart/`
Satisfies FR-002. Returns (creating on first access, research.md §1) the authenticated Customer's
cart with every line's live price/availability and a total that excludes unavailable lines
(data-model.md).

Response `200`:
```json
{
  "id": 1,
  "items": [
    { "id": 10, "product": { "id": 5, "name": "USB-C Cable", "shop_name": "Kofi's Electronics" },
      "quantity": 2, "unit_price": "9.99", "subtotal": "19.98", "is_available": true },
    { "id": 11, "product": { "id": 9, "name": "Discontinued Widget", "shop_name": "Ama's Store" },
      "quantity": 1, "unit_price": "4.50", "subtotal": "4.50", "is_available": false,
      "unavailable_reason": "no longer published" }
  ],
  "total": "19.98"
}
```
`total` sums only lines where `is_available: true` (User Story 3 Scenario 2). An empty cart
returns `"items": []`, `"total": "0.00"` — a normal `200`, not an error (Edge Cases).

### `POST /api/cart/items/`
Satisfies FR-001, FR-005, FR-007. Request: `{ "product_id": 5, "quantity": 2 }`.

If `product_id` is already a line in the cart, its `quantity` is incremented by the requested
amount (FR-005) rather than creating a new line; the combined quantity is still validated against
current stock (FR-007).

Response `201` (new line) or `200` (merged into existing line): the affected `CartItem`, same
shape as a cart response line.
Errors: `400` `{ "quantity": ["Only 12 available."] }` when requested/combined quantity exceeds
`product.stock_quantity` (FR-007); `400` product not found, not published, or its shop not
APPROVED (a Customer can't add an item that was never a valid catalog listing to begin with);
`400` `quantity < 1`.

### `PATCH /api/cart/items/{id}/`
Satisfies FR-003. Request: `{ "quantity": 5 }`. Only the requester's own line is reachable — any
other Customer's line ID 404s (research.md §6).

Response `200`: updated line. Errors: `400` quantity exceeds current stock (FR-007); `404` not
the requester's line.

### `DELETE /api/cart/items/{id}/`
Satisfies FR-004. Removes exactly one line; other lines and the recomputed total are unaffected.

Response `204`. Errors: `404` not the requester's line.

## Checkout (`/api/checkout/`)

### `POST /api/checkout/`
Satisfies FR-008 through FR-017. Runs `orders.services.place_order()` (research.md §4) inside one
atomic transaction: re-validates every cart line against current `Product`/`Shop` state, charges
the mock payment service, and — only if both succeed — creates the `Order` (+ `OrderItem`s +
`PaymentRecord`), decrements stock, and empties the cart. Any failure leaves the cart, stock, and
order history completely unchanged (FR-016).

Request:
```json
{
  "shipping": {
    "recipient_name": "Ama Owusu", "address_line": "12 Ring Road",
    "city": "Accra", "region": "Greater Accra", "postal_code": "GA-184-9021",
    "country": "Ghana", "phone": "+233201234567"
  },
  "payment_method": "card"
}
```

Response `201`: the created `Order` in the same shape as `GET /api/orders/{id}/` (see below).

Errors (all `400`, no `Order` created, no stock decremented, cart unchanged):
- Empty cart, or a cart whose only lines are unavailable (FR-011):
  `{ "detail": "Your cart is empty." }`
- One or more lines failed re-validation (FR-008, User Story 3 Scenario 3):
  `{ "detail": "Some items in your cart are no longer available.",
     "lines": [ { "cart_item_id": 11, "reason": "no longer published" } ] }`
- Missing/invalid shipping field (FR-010): `{ "shipping": { "postal_code": ["This field is
  required."] } }`
- Payment declined (FR-016, research.md §5 — sentinel `payment_method: "declined"` deterministically
  triggers this in tests): `{ "detail": "Payment was declined.", "code": "payment_failed" }`

## Order history (`/api/orders/`)

### `GET /api/orders/`
Satisfies FR-020. Lists only the authenticated Customer's own orders, paginated, most recent
first (`-placed_at`).

Response `200`:
```json
{
  "count": 2, "next": null, "previous": null,
  "results": [
    { "id": 42, "placed_at": "2026-09-18T10:15:00Z", "status": "PLACED", "total": "19.98" }
  ]
}
```

### `GET /api/orders/{id}/`
Satisfies FR-019, FR-020, FR-021. `404` if the order doesn't exist or doesn't belong to the
requester (research.md §6) — the same shape in both cases, so a Customer can't distinguish "never
existed" from "exists but isn't yours."

Response `200`:
```json
{
  "id": 42, "placed_at": "2026-09-18T10:15:00Z", "status": "PLACED", "total": "19.98",
  "shipping": { "recipient_name": "Ama Owusu", "address_line": "12 Ring Road", "city": "Accra",
    "region": "Greater Accra", "postal_code": "GA-184-9021", "country": "Ghana",
    "phone": "+233201234567" },
  "items": [
    { "id": 100, "product": { "id": 5, "name": "USB-C Cable" }, "shop_name": "Kofi's Electronics",
      "quantity": 2, "unit_price": "9.99", "subtotal": "19.98", "status": "PENDING" }
  ],
  "payment": { "method": "card", "status": "SUCCEEDED" }
}
```

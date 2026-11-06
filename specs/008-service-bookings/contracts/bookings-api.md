# API Contract: Service Bookings

Lists are paginated with `PaginatedResponse`. Errors use the existing `{"detail": "..."}` or field-error shapes. Times are ISO 8601 with `+03:00`, and money is a decimal string in TZS.

Status codes:
- **400**: the request is invalid, such as a time no longer being available.
- **403**: the role or permission is wrong, the email is unverified, or the shop isn't approved.
- **404**: the record doesn't exist or belongs to someone else.
- **409**: the action doesn't fit the booking's current status.

## Public

| Method and path | Purpose |
|---|---|
| `GET /api/catalog/services?search=&category=&shop=&page=` | Published services of approved shops |
| `GET /api/catalog/services/{id}` | Service details and shop summary |
| `GET /api/catalog/services/{id}/slots?date=YYYY-MM-DD` | Open times for one Dar es Salaam date |
| `GET /api/catalog/categories?kind=SERVICE` | Service categories. Without `kind`, it returns product categories as it does today |

`slots` returns:

```json
{
  "date": "2026-11-20",
  "time_zone": "Africa/Dar_es_Salaam",
  "slots": [{ "starts_at": "2026-11-20T09:00:00+03:00", "ends_at": "2026-11-20T10:00:00+03:00" }]
}
```

## Customer

Requires a signed-in customer. Creating a booking also requires a verified email.

| Method and path | Purpose |
|---|---|
| `POST /api/bookings` | Request a time |
| `GET /api/bookings?status=` | Own bookings |
| `GET /api/bookings/{id}` | One booking, with status history and payment state |
| `GET /api/bookings/{id}/payment-methods` | Methods available for this booking |
| `POST /api/bookings/{id}/pay` | Start a payment attempt |
| `GET /api/bookings/{id}/payment-status` | Current payment state |
| `POST /api/bookings/{id}/cancel` | Cancel under the customer rules |

`POST /api/bookings` body:

```json
{ "service": 12, "starts_at": "2026-11-20T09:00:00+03:00", "contact_phone": "+255712345678", "customer_note": "" }
```

`POST /api/bookings/{id}/pay` body, by method:

```json
{ "payment_method": "mobile_money", "provider": "Mpesa", "msisdn": "0712345678" }
```

```json
{ "payment_method": "lipa_namba", "payer_reference": "ABC123XYZ" }
```

No amount is accepted. The server uses `Booking.amount_due()`. `card` and `cod` aren't offered for bookings. A second attempt while one is live returns 409.

## Provider

Requires the owner of the shop. Writes also require an APPROVED shop.

| Method and path | Purpose |
|---|---|
| `GET`, `POST /api/vendor/services` | List and create services |
| `GET`, `PATCH`, `DELETE /api/vendor/services/{id}` | Read, edit and archive |
| `POST /api/vendor/services/{id}/publish`, `/unpublish` | Change visibility |
| `GET`, `PUT /api/vendor/shops/{id}/schedule` | Weekly hours and capacity; `PUT` replaces them |
| `GET`, `POST /api/vendor/shops/{id}/closures` | List and add closures. `POST` returns any active bookings on that date as a warning |
| `DELETE /api/vendor/shops/{id}/closures/{closure_id}` | Remove a closure |
| `GET /api/vendor/bookings?status=&shop=` | Bookings for own shops |
| `GET /api/vendor/bookings/{id}` | One booking |
| `POST /api/vendor/bookings/{id}/accept` | Accept a request |
| `POST /api/vendor/bookings/{id}/decline` | Decline, with an optional reason |
| `POST /api/vendor/bookings/{id}/cancel` | Cancel, with a required reason |
| `POST /api/vendor/bookings/{id}/complete` | Mark completed, after the start time |
| `POST /api/vendor/bookings/{id}/no-show` | Mark no-show, after the start time |

## Admin

| Method and path | Permission | Purpose |
|---|---|---|
| `GET /api/admin/bookings?status=&shop=&search=&date_from=&date_to=` | `bookings.view` | All bookings |
| `GET /api/admin/bookings/{id}` | `bookings.view` | One booking |
| `POST /api/admin/bookings/{id}/cancel` | `bookings.manage` | Body: `reason`, `refund_amount` |
| `POST /api/admin/bookings/{id}/payment/confirm` | `finance.manage` | Confirm a Lipa Namba payment |
| `POST /api/admin/bookings/{id}/payment/reject` | `finance.manage` | Reject it, with a reason |
| `GET /api/admin/refunds?status=` | `finance.view` | The refund list |
| `POST /api/admin/refunds/{id}/mark-paid` | `finance.manage` | Body: `paid_reference`. A repeat returns 409 |

Tier grants: Super Admin gets all of these. Support Admin gets `bookings.view` and `bookings.manage`, but no finance permissions.

## Changes to existing endpoints

- **Shop request:** accepts `business_type`, which is required for new requests from the frontend and defaults to GOODS for other clients. Shop serializers return `business_type` and `booking_capacity`.
- **Vendor products:** creating a product in a SERVICES shop returns 403.
- **Admin categories:** accepts and returns `kind`.
- **Finance:**
  - Balances, summaries and payouts include booking amounts.
  - Payout details list bookings.
  - Transactions add a nullable `booking_id`, and `order_id` becomes nullable.
  - The summary adds `booking_count`.
- **Dev simulator:** shows a booking reference when the payment has no order.

## Live events

Hints sent over the existing WebSocket, after which clients refetch over REST:

| Event | Audience |
|---|---|
| `booking.created` | Shop owner, admins |
| `booking.updated` | Customer, shop owner, admins |
| `refund.updated` | Admins |

Payload: `{"type": "booking.updated", "booking_id": 42}`.

## Scheduled command

`python manage.py expire_bookings` settles stale mobile-money payments on bookings and then expires overdue bookings. It is safe to run repeatedly and prints how many it changed.

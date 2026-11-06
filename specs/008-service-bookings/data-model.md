# Data Model: Service Bookings

Times are stored in UTC unless noted. Money uses `DecimalField(max_digits=12, decimal_places=2)`.

## Changes to existing models

### `vendors.Shop`

| Field | Type | Rules |
|---|---|---|
| `business_type` | GOODS or SERVICES | Default GOODS. Set when the shop is requested; read-only afterwards |
| `booking_capacity` | Positive integer | Default 1, minimum 1. Editable by the owner of an approved shop |

### `catalog.Category`

| Field | Type | Rules |
|---|---|---|
| `kind` | PRODUCT or SERVICE | Default PRODUCT. A subcategory takes its parent's kind. Can't change while in use |

`validate_category` on products refuses SERVICE categories. The category delete guard also checks services. The unique top-level name constraint becomes per kind, so a seeded product category such as Beauty doesn't block a Beauty service category.

### `payments.PaymentRecord`

| Field | Change |
|---|---|
| `order` | Becomes nullable |
| `booking` | New nullable FK to `bookings.Booking`, PROTECT, `related_name="payments"` |

Constraints:
- `payment_has_one_target`: exactly one of `order` and `booking` is set.
- `one_live_payment_per_booking`: unique on `booking` where status is PENDING or SUCCEEDED.

## New in `apps.bookings`

### `Service`

| Field | Type | Rules |
|---|---|---|
| `shop` | FK Shop, PROTECT | Must be a SERVICES shop |
| `category` | FK Category, PROTECT | Must be a SERVICE category, following the existing subcategory rule |
| `name` | Char(255) | Unique among a shop's unarchived services, so an archived name can be reused |
| `description` | Text | May be blank |
| `price` | Decimal | Above 0 |
| `duration_minutes` | Positive integer | Multiple of the slot step; 30 to 1440 |
| `is_published` | Boolean | Default false. Publishing needs an approved shop with a location |
| `is_archived` | Boolean | Default false. Archived means unpublished, hidden from new bookings, kept for history |
| `created_at`, `updated_at` | Datetime | |

### `OpeningHours`

| Field | Type | Rules |
|---|---|---|
| `shop` | FK Shop, CASCADE | |
| `weekday` | 0 to 6 | Monday is 0 |
| `opens_at`, `closes_at` | Local time | `closes_at` after `opens_at`; same-day periods only; periods on one day can't overlap |

### `ShopClosure`

| Field | Type | Rules |
|---|---|---|
| `shop` | FK Shop, CASCADE | |
| `date` | Local date | Unique per shop |
| `note` | Char(255) | May be blank |

### `Booking`

| Field | Type | Rules |
|---|---|---|
| `customer` | FK User, PROTECT | |
| `shop` | FK Shop, PROTECT | Copied from the service, for locking and finance |
| `service` | FK Service, PROTECT | |
| `status` | See below | Default REQUESTED |
| `starts_at`, `ends_at` | Datetime | `ends_at` is after `starts_at` |
| `respond_by` | Datetime | `min(created + 12h, starts_at − 90m)` |
| `pay_by` | Datetime, nullable | Set on acceptance: `min(accepted + 6h, starts_at − 60m)` |
| `contact_phone` | Char(20) | Required; existing phone validator |
| `customer_note` | Text | May be blank |
| `status_reason` | Text | Required for a provider or admin cancellation |
| `price` | Decimal | Fixed at request |
| `commission_rate` | Decimal(5,2) | Fixed at request, from `shop.effective_commission_rate()` |
| `commission_amount`, `vendor_earning` | Decimal | Fixed at request, from `finance.services.split_line()` |
| `payout` | FK Payout, SET_NULL, nullable | `related_name="bookings"` |
| `created_at`, `accepted_at`, `confirmed_at`, `completed_at`, `cancelled_at` | Datetime | Timestamps are nullable except `created_at` |

Indexes: `(shop, starts_at)`, `(customer, status)`, `(status, respond_by)`, `(status, pay_by)`.

`amount_due()` returns `price`. Feature `009` adds the ride fee here.

### `BookingStatusEvent`

Append-only: `booking`, `status`, `actor` (nullable; empty means the system), `reason`, `created_at`.

## New in `apps.payments`

### `RefundDue`

| Field | Type | Rules |
|---|---|---|
| `payment` | FK PaymentRecord, PROTECT | Unique together with `reason` |
| `amount` | Decimal | Above 0, and no more than the payment's amount |
| `reason` | CUSTOMER_CANCELLED, PROVIDER_CANCELLED, ADMIN_CANCELLED, LATE_PAYMENT | |
| `note` | Text | May be blank |
| `status` | DUE or PAID | Default DUE |
| `paid_reference` | Char(128) | Required when PAID |
| `paid_by` | FK User, SET_NULL, nullable | |
| `paid_at` | Datetime, nullable | |
| `created_at` | Datetime | |

## Booking status flow

| From | Event | To | Who |
|---|---|---|---|
| (new) | Request an open time | REQUESTED | Customer |
| REQUESTED | Accept, before `respond_by` | AWAITING_PAYMENT | Provider |
| REQUESTED | Decline | DECLINED | Provider |
| REQUESTED | `respond_by` passes | EXPIRED | System |
| REQUESTED | Cancel | CANCELLED | Customer or Administrator |
| AWAITING_PAYMENT | Payment succeeds, with the time still held and the visit not started | CONFIRMED | System or Administrator |
| AWAITING_PAYMENT | `pay_by` passes with no payment in progress, or the visit starts | EXPIRED | System |
| AWAITING_PAYMENT | Cancel, with no payment in progress | CANCELLED | Customer, provider or Administrator |
| CONFIRMED | Cancel at least 24h before the visit | CANCELLED + RefundDue | Customer |
| CONFIRMED | Cancel with a reason | CANCELLED + RefundDue | Provider or Administrator |
| CONFIRMED | Mark completed, after `starts_at` | COMPLETED | Provider |
| CONFIRMED | Mark no-show, after `starts_at` | NO_SHOW | Provider |

DECLINED, EXPIRED, CANCELLED, COMPLETED and NO_SHOW are final. A failed payment doesn't change the booking's status.

**Held times**: see `research.md` section 5. **Active unpaid** bookings are those holding a time with status REQUESTED or AWAITING_PAYMENT.

Every status change goes through `bookings.services`, runs in a transaction with the booking row locked, and writes one `BookingStatusEvent`.

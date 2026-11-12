# Research: Service Bookings

Decisions come from reading the current code. The Technical Context has no open questions.

## 1. Booking as its own model

**Decision**: Add `apps.bookings.Booking`; don't represent bookings as `Order` and `OrderItem`.

**Rationale**: `OrderItem.product` is required, and stock release, vendor audiences and finance joins all depend on it. `Order.PLACED` means paid, but a provider must see a booking before payment. `SHIPPED` and `DELIVERED` don't describe a service.

**Alternatives considered**: A shadow product per service would pull in stock and cart behaviour.

## 2. One payment table

**Decision**: Make `PaymentRecord.order` nullable, and add a nullable `booking` FK with a check that exactly one is set. A partial unique constraint allows one PENDING or SUCCEEDED record per booking.

**Rationale**: The callback lookup, expiry, simulator and transaction list stay in one place. A FK rather than a one-to-one allows retries after failure, and the constraint prevents double charging.

**Alternatives considered**: A separate `BookingPayment` table duplicates settlement and needs a union to paginate transactions. A generic foreign key loses integrity and breaks `order__payment__status`.

## 3. Payment settlement

**Decision**: Split `complete_payment()`. The shared start keeps the lock and idempotency check; the current body becomes `_apply_order_outcome`; booking records call `bookings.services.on_payment_settled` through a local import, as the module already does for `send_order_confirmation`.

**Rationale**: It's the smallest change that keeps goods behaviour the same. Existing tests, unedited, check this.

**Code that needs a booking branch**:
- `_audit_system_payment`, `_announce_payment` and `settle_manual_payment` in `apps/payments/outcomes.py`
- `filter_transactions` in `apps/finance/services.py`, and the transaction serializer and report template
- The simulator view and its dev page

Reverse access through `order.payment` is unaffected.

## 4. Late payments and Lipa Namba

**Decision**:
- `handle_azampay_callback` sends a success on a booking's FAILED record to `reconcile_late_payment`.
- A late success confirms the booking only if the booking is AWAITING_PAYMENT, `pay_by` hasn't passed, the visit hasn't started, and no other live payment exists. Otherwise it creates a `RefundDue`.
- A `RefundDue` is unique per payment and reason, so repeated callbacks can't duplicate it.
- A booking's Lipa Namba record doesn't expire on the timer. `expire_stale_payments` excludes those records from its Lipa branch.
- When the visit time passes, a booking with an unsettled Lipa record becomes EXPIRED and the record stays PENDING. If an Administrator then confirms the money arrived, it becomes a `RefundDue`.

**Rationale**: The customer's money could otherwise be lost: a Lipa Namba timer could fail a payment the Administrator hasn't checked yet. This satisfies SC-004. Requiring `pay_by` not to have passed means the time was held throughout, so capacity doesn't need rechecking.

## 5. Availability and double booking

**Decision**: `request_booking` runs in one transaction: lock the customer row, then the shop row, both with `select_for_update(no_key=True)`, regenerate the open times, check that the start time is offered, compute peak overlap against capacity, and insert. Capacity and hours are per shop.

**Rationale**: One salon chair is shared by all services. `no_key` doesn't block rows that only reference the shop. It follows the locking approach of checkout. The customer lock exists because the limit on active unpaid bookings spans shops, so the shop lock alone can't protect it.

**Alternatives considered**: An exclusion constraint can't express capacity above 1. Pre-built slot rows can't handle mixed durations well.

**What holds a time** is defined in one queryset method, `Booking.objects.holding(now)`:
- REQUESTED with `respond_by` after now
- AWAITING_PAYMENT with `pay_by` after now, or with a PENDING payment
- CONFIRMED

Because it compares deadlines, times free up on schedule even if cron stops.

## 6. Time zones

**Decision**: Keep `TIME_ZONE = "UTC"` and add `MARKET_TIME_ZONE = "Africa/Dar_es_Salaam"`. Opening hours are local times, converted with `ZoneInfo`. The API returns ISO times with `+03:00`. The frontend formats with `Intl` and a fixed `timeZone`, with no date library. Add `tzdata` to `requirements.txt` so the zone exists in every environment.

**Rationale**: Changing the global setting could affect existing date filters and reports.

## 7. Expiry

**Decision**: Add `manage.py expire_bookings`, run every 5 minutes from cron, plus an expiry pass before booking reads and provider actions. All rule values are env settings.

**Rationale**: It matches the repo's lazy pattern and needs no new service. A task queue was rejected earlier as too heavy, and that still holds.

**Lock order**: payment record first, then booking. The sweep settles records first, then locks each booking and only reads its records, which avoids deadlocks with callbacks.

**Settings and defaults**:

| Setting | Default |
|---|---|
| `BOOKING_RESPONSE_HOURS` | 12 |
| `BOOKING_RESPONSE_BUFFER_MINUTES` | 90 |
| `BOOKING_PAYMENT_HOURS` | 6 |
| `BOOKING_PAYMENT_BUFFER_MINUTES` | 60 |
| `BOOKING_MIN_NOTICE_HOURS` | 3 |
| `BOOKING_MAX_ADVANCE_DAYS` | 60 |
| `BOOKING_SLOT_MINUTES` | 30 |
| `BOOKING_MAX_ACTIVE_UNPAID` | 3 |
| `BOOKING_CUSTOMER_CANCEL_HOURS` | 24 |
| `BOOKING_LIPA_MIN_HOURS` | 3 |

## 8. Catalogue

**Decision**: Add a separate `Service` model and `Category.kind`. `Shop.business_type` defaults to GOODS, and the migration leaves existing shops as goods. `CategoryListView` keeps returning product categories unless asked for another kind.

**Rationale**: `Product` carries stock, cart, images and reviews, and its publish rule requires stock. `Category.kind` reuses the admin screens, where a separate table would need new management screens.

## 9. Finance

**Decision**: Add `Booking.payout` (`related_name="bookings"`), mirroring `OrderItem.payout`. Goods aggregates stay as they are, and booking totals are added through `Subquery` on the `Shop` queries, or computed separately and added in Python on `shop_balance` and `platform_summary`.

**Rationale**: `Shop.annotate(Sum("products__order_items__…"))` would multiply every total if a second multi-valued join were added, which would overpay shops. Sorting by `-available_balance` happens in SQL, so the combined value must be a SQL expression. Combining an aggregate with a subquery is expected to work in Django, and a mixed-shop test must prove it.

**Booking status mapping**:

| Figure | Booking statuses |
|---|---|
| `gross_sales` | CONFIRMED, COMPLETED, NO_SHOW |
| `pending_earnings`, `commission_pending` | CONFIRMED |
| `commission_earned` | COMPLETED, NO_SHOW |
| `available_balance` | COMPLETED, NO_SHOW, with `payout` empty |
| `in_payout`, `paid_out` | Based on payout status, as for order lines |

`payout_queryset` must use `Count(..., distinct=True)` on both items and bookings.

## 10. Access

**Decision** (amended 2026-11-09): Allow a signed-in customer with a verified email (`require_verified_email`) **or** a guest with no account, using the existing `IsCustomerOrGuest`, the same as guest checkout. A guest gives a name and email. The booking has a null customer, a `guest_email` and an unguessable `access_token`, and the guest follows it at `/bookings/track/{token}`, a link that is also emailed to them. Refuse bookings on a signed-in customer's own shop. The per-IP `booking_request` throttle and the 3-active-unpaid limit (counted per guest email, serialised with a Postgres advisory lock) guard against anonymous holds.

**Rationale**: The original sign-in requirement was relaxed so customers can book without registering. Email is still the outbound channel, so a guest must give one. There is no email verification step, so the throttle and the per-email unpaid limit are what keep capacity from being blocked cheaply.

## 11. Provider cancellation before payment

**Decision**: Providers can also cancel an AWAITING_PAYMENT booking with no payment in progress, giving a reason. No money is owed.

**Rationale**: The spec tells providers to cancel bookings on a day they later close. Requests can be declined and confirmed bookings cancelled, so this closes the remaining gap.

## 12. Next.js guides (T001)

**Checked**: `use-client` and `use-params` in `frontend/node_modules/next/dist/docs/`. Booking pages are client components that read the id with `useParams`, as the existing service and order pages do. Nothing in these guides changes that approach.

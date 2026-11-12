# Quickstart: Validating Service Bookings

These checks prove each user story works. Use [contracts/bookings-api.md](contracts/bookings-api.md) for request details and [data-model.md](data-model.md) for status rules.

## Setup

Backend, from `backend/`, with the Postgres container on port 5433:

```powershell
docker compose up -d
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver
```

Set `PAYMENT_BACKEND=azampay_simulator` and enable `lipa_namba` in `MANUAL_PAYMENT_METHODS`, with a till set, to test both payment methods.

Frontend, from `frontend/`:

```powershell
npm run dev
```

If port 3000 is taken, pass `-p`, and add that origin to `CORS_ALLOWED_ORIGINS`.

## Automated checks

From `backend/`:

```powershell
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\ruff check .
```

From `frontend/`:

```powershell
npm run lint
npm run format:check
npm run test
npm run build
```

## US1: Catalogue and open times

1. Request a shop as a services business and approve it as an Administrator.
2. Try to publish a service before setting a location. **Expected:** refused.
3. Set a location, publish a 60-minute service, and set hours of 09:00 to 17:00.
4. As a guest, open the service and pick a date. **Expected:** the last time is 16:00, labelled in Dar es Salaam time.
5. Change the browser's time zone. **Expected:** the times shown don't change.
6. Mark that date closed. **Expected:** no times are offered.

## US2: Requests and responses

1. Request a time as a verified customer. **Expected:** with capacity 1, the time disappears, along with overlapping times on other services.
2. Decline it as the provider. **Expected:** the time returns, and no payment is requested.
3. Request again and accept. **Expected:** the customer sees a payment deadline.
4. Set a test booking's `respond_by` in the past. **Expected:** the time is free before running the command, and `expire_bookings` then marks it EXPIRED.
5. Run the command again. **Expected:** it changes nothing.
6. Create 3 active unpaid bookings and try a fourth. **Expected:** refused.
7. Open another customer's booking. **Expected:** not found.

## US3: Payment and refunds

1. Pay by mobile money and approve on the simulator's phone page. **Expected:** CONFIRMED.
2. On another booking, reject the push and retry. **Expected:** it stays awaiting payment, and the retry succeeds.
3. While a push is pending, try to pay again and to cancel. **Expected:** both refused.
4. Pay by Lipa Namba and confirm as a finance Administrator. **Expected:** CONFIRMED.
5. Let a mobile-money payment expire, then send its success callback. **Expected:** the booking is confirmed if it can still be honoured, and otherwise a refund entry appears. Repeating the callback changes nothing.
6. Cancel a confirmed booking as the provider, with a reason. **Expected:** a full-amount entry appears on `/admin/refunds`.
7. Mark it paid, and try again. **Expected:** the second attempt is refused.
8. As a customer, try to cancel a paid booking less than 24 hours away. **Expected:** refused, with a message to contact support.
9. Place a goods order through checkout. **Expected:** it works as before.

## US4: Completion and earnings

1. Try to complete a booking before its start time. **Expected:** refused.
2. After the start time, mark it completed. **Expected:** the shop's available balance rises by the booking's earning.
3. Use a shop with both goods and booking earnings. **Expected:** each figure on `/vendor/earnings` and `/admin/finance` is the exact sum.
4. Pay the shop out. **Expected:** the statement lists both kinds of line.
5. Force a payout failure. **Expected:** those bookings are available for payout again.
6. Open `/admin/transactions`. **Expected:** the booking's payment links to the booking, and the PDF report renders.

## Results: 2026-11-12

Walked through locally against the dev database, with `azampay_simulator`, Lipa Namba till `555123` and the `mock` disbursement backend. Port 8000 was taken by another project's container, so this ran with the backend on `8010`, and the frontend was started with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8010`. Test accounts were `provider.walk@` and `customer.walk@emall.local`, with passwords in `backend/.env`, plus the seeded admin. The shop was "Walk Salon Services" (#76), offering Haircut (60 min, TSh 20,000) and Beard trim (30 min, TSh 8,000).

### Automated checks

| Check | Result |
| --- | --- |
| `pytest` | 861 passed, **5 failed**: all in `tests/finance/test_reports.py`, `AttributeError: 'super' object has no attribute 'dicts'` in `Context.__copy__`. This comes from the local venv running Python 3.14 with Django 5.1, which doesn't support it. It only happens under the test client's template instrumentation, and production runs Python 3.12. The PDFs render fine in the running app (see US4.6). Not caused by this feature. |
| `ruff check .` | Pass |
| `npm run lint` | Pass |
| `npm run format:check` | Pass |
| `npm run test` | Pass (113 tests) |
| `npm run build` | Pass |

### US1

| Step | Result | Notes |
| --- | --- | --- |
| 1 | Pass | Services shop requested from Account, then approved in Shop approvals. |
| 2 | Pass | Publish refused: "Set your shop's location before publishing a service." |
| 3 | Pass | Location pinned, service published, hours 09:00–17:00 every day. |
| 4 | Pass | As a guest on 13 Nov, the times run 09:00–16:00, "in Dar es Salaam time". |
| 5 | Pass (substitute) | The browser zone couldn't be changed from automation. Every formatter in `lib/market-time.ts` pins `Africa/Dar_es_Salaam`, and `market-time.test.ts` passes under `TZ=America/New_York` and `TZ=Asia/Tokyo`. |
| 6 | Pass | 14 Nov marked closed: "No open times". |

### US2

| Step | Result | Notes |
| --- | --- | --- |
| 1 | Pass | With 10:00 held, Haircut lost 09:30, 10:00 and 10:30, and Beard trim lost 10:00 and 10:30 but kept 09:30. |
| 2 | Pass | Declined with a reason: the times returned and no payment record was created. |
| 3 | Pass | Accepted: the customer sees "Pay by Fri, 13 Nov 2026 at 00:08". |
| 4 | Pass | `respond_by` back-dated: the time was free before the command ran, then `expire_bookings` marked the booking EXPIRED. |
| 5 | Pass | The second run reported "Expired 0". |
| 6 | Pass | 4th active unpaid booking refused: "You already have 3 bookings waiting…" |
| 7 | Pass | Another customer's booking returns 404 in the API, and the page shows "Booking not found". |

### US3

| Step | Result | Notes |
| --- | --- | --- |
| 1 | Pass | Mobile money approved on `/dev/azampay-sandbox`: CONFIRMED, and the customer page updated live. |
| 2 | Pass | Push rejected: still awaiting payment, with the reason shown. The retry was approved: CONFIRMED. |
| 3 | Pass | While a push was pending, pay and cancel both returned 409. |
| 4 | Pass | Lipa Namba transaction ID submitted, then "Confirm payment → Yes, received" as admin: CONFIRMED. |
| 5 | Pass | Payment and booking expired, then a success callback was sent: payment SUCCEEDED, booking stays EXPIRED, and a LATE_PAYMENT refund is DUE (research.md §7). The repeated callback changed nothing. |
| 6 | Pass | Provider cancelled a confirmed booking with a reason: a TSh 20,000 PROVIDER_CANCELLED entry appears on `/admin/refunds`. |
| 7 | Pass | Marked paid. A second attempt returned 409 "already been paid". |
| 8 | Pass | Less than 24h away: cancel is hidden, the page says to contact support, and the API returns 409. |
| 9 | Pass | Goods order #64 paid by mobile money: payment SUCCEEDED, order PLACED. |

### US4

| Step | Result | Notes |
| --- | --- | --- |
| 1 | Pass | Before the start, the buttons are hidden ("from Fri … at 11:00"), and complete and no-show return 409. |
| 2 | Pass | Visit times back-dated. Completed plus no-show: available went from TSh 0 to TSh 25,200 (18,000 + 7,200), and the earnings page matches the database. |
| 3 | Pass (platform level) | A shop is goods or services and can't change, so a shop with both can't be reached in the UI; T073 covers that case. Every mall-wide figure on `/admin/finance` equals the exact sum over all shops. |
| 4 | Pass | PAYOUT-9 succeeded and lists bookings #26 and #28. The statement PDF contains both. |
| 5 | Pass | Failing mock phone: payout #8 FAILED, both bookings were released (`payout_id` null), and the balance stayed available. The retry succeeded. |
| 6 | Pass | Booking payments link to `/admin/bookings/<id>`. The transaction, finance and payout PDFs render, with booking rows. |

### Fixed during the walkthrough

- `components/booking/slot-picker.tsx`: the selected time used `bg-primary`, which the theme doesn't define, so it showed white text on white and the chosen time looked like it had vanished. It now uses `bg-navy-900`, like other selected controls.
- `components/booking/booking-payment-panel.tsx`: the failure message ran into the next sentence ("…rejected the payment You can try again."). It now adds a full stop when the reason has none.

### Noted, not fixed

- Location section on a services shop: it says "Customers can't check out your products … delivery fee" and labels the fields "Pickup address/location". This is goods wording.
- The Shop approvals badge keeps its count after an approval until the page reloads.
- Admin Lipa Namba confirmation is credited to "System" in the booking history, not to the admin.
- Booking create, accept and decline take about 2.7s, because the status email is sent over SMTP inside the request. Goods orders do the same.
- Goods (existing behaviour, not from this feature): after a mobile-money order is paid, the cart badge still shows the old count until the next reload. The server cart is empty.
- Payouts (existing): a failure message reads "Mock: recipient rejected.." with a doubled full stop.

## Required automated tests

- **Concurrency:** threaded tests modelled on `backend/tests/orders/test_checkout_concurrency.py`.
- **Slots:** UTC+3 around midnight, closures, mixed durations and capacity above 1.
- **Status rules:** every allowed and refused transition.
- **Payments:** callback, retry, wrong amount, late success in each status, Lipa Namba after the visit starts, and success racing expiry.
- **Finance:** totals and payouts for a shop with both goods and bookings.
- **Permissions:** every endpoint by role and admin tier, including additions to `tests/core/test_admin_permissions.py`.

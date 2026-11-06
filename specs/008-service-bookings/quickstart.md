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

## Required automated tests

- **Concurrency:** threaded tests modelled on `backend/tests/orders/test_checkout_concurrency.py`.
- **Slots:** UTC+3 around midnight, closures, mixed durations and capacity above 1.
- **Status rules:** every allowed and refused transition.
- **Payments:** callback, retry, wrong amount, late success in each status, Lipa Namba after the visit starts, and success racing expiry.
- **Finance:** totals and payouts for a shop with both goods and bookings.
- **Permissions:** every endpoint by role and admin tier, including additions to `tests/core/test_admin_permissions.py`.

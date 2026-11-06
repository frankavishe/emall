# Implementation Plan: Service Bookings

**Branch**: `feature/service-bookings` | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-service-bookings/spec.md`

## Summary

Let approved services shops list bookable services. Customers request an open time, the provider accepts or declines, and the customer pays after acceptance. Providers then mark the visit complete and earn through the existing payouts.

The work adds a new `apps.bookings` app with its own `Booking` model. It connects to existing code at two points: `PaymentRecord` gains a nullable `booking` link, and finance totals gain booking amounts through subqueries. Rides (`009`) and cash at the visit (`010`) are not built here, but `Booking.amount_due()` and `RefundDue.Reason` leave room for them.

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript with React 19 (frontend)

**Primary Dependencies**: Django 5.1, DRF 3.15, Channels 4; Next.js 16.3.5, Tailwind 4. One new package: `tzdata`.

**Storage**: PostgreSQL 16

**Testing**: pytest against real Postgres, `ruff`; Vitest, Playwright, ESLint, Prettier

**Target Platform**: Linux containers on the Contabo VPS; desktop and mobile browsers

**Project Type**: Web application (Django API and Next.js frontend)

**Performance Goals**: Open times for one date return in under 1 second for a shop with up to 200 live bookings that day. This is a planning target.

**Constraints**:
- Booking must be correct under simultaneous requests.
- Goods checkout behaviour must not change.
- No task queue; scheduled work runs from cron.
- All amounts are in TZS, and all displayed times are in `Africa/Dar_es_Salaam`.

**Scale/Scope**: One city, one market time zone, and about 7 new models and 30 endpoints, delivered as 4 user stories.

## Constitution Check

*Checked against constitution 1.2.0, before research and again after design.*

| Principle | How this feature complies | Result |
|---|---|---|
| I. Roles and least privilege | Permissions are checked on the server. A new `bookings.view` and `bookings.manage` area is added; payment settlement and refunds need `finance.manage`. Other people's bookings return 404 through queryset filters. | Pass |
| II. Approval gate | Creating, publishing or changing services, receiving requests and accepting them all check for an APPROVED shop on the server. | Pass |
| III. Data and payment security | No card data is stored. Amounts are computed by the server. The existing callback token and amount check are reused. | Pass |
| IV. Real core, mocked edges | Booking, capacity and state changes are real. Payment, email and disbursement keep their existing swappable services. | Pass |
| V. Staged delivery | Delivered one user story at a time. Each chunk is run for real before the next, and the artifacts are reviewed first. | Pass |
| VI. Simplicity | Protected structures are unchanged. Capacity is one per-shop figure, and there is no staff calendar or slot table. `RefundDue` is a manual list, not a refund system. | Pass |
| Reliability and resource rules | State changes are transactional, lists are paginated, and serializers use `select_related`. | Pass |
| Traceability | Every model and endpoint maps to a requirement in the spec. | Pass |

No violations, so Complexity Tracking is omitted.

## Project Structure

### Documentation (this feature)

```text
specs/008-service-bookings/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/bookings-api.md
├── checklists/requirements.md
└── tasks.md             # Created by /speckit-tasks
```

### Source Code

```text
backend/
├── apps/bookings/              # New
│   ├── models.py               # Service, OpeningHours, ShopClosure, Booking, BookingStatusEvent
│   ├── slots.py                # Open times and capacity
│   ├── services.py             # The only code that changes booking status
│   ├── serializers.py, views.py, urls.py, permissions.py
│   └── management/commands/expire_bookings.py
├── apps/payments/              # RefundDue; PaymentRecord link; complete_payment split
├── apps/finance/               # Booking earnings in balances, payouts, reports
├── apps/vendors/, apps/catalog/ # Shop type and capacity; category kind; shop-type guards
├── apps/audit/, apps/core/     # Audit actions, admin area, booking emails
├── apps/realtime/groups.py     # Booking audience
├── config/settings.py, config/urls.py, requirements.txt
└── tests/bookings/             # New; plus additions in tests/finance and tests/core

frontend/src/
├── app/services/, app/bookings/                    # Customer
├── app/vendor/services/, app/vendor/schedule/, app/vendor/bookings/  # Provider
├── app/admin/bookings/, app/admin/refunds/         # Admin
├── components/payment/payment-method-fields.tsx    # Extracted from checkout
├── components/booking/                             # Slot picker, status, payment panel
├── lib/market-time.ts                              # Dar es Salaam formatting
└── lib/api-client.ts, lib/realtime.ts, components/nav.tsx, components/admin-sidebar.tsx

docs/deploy-contabo.md                              # expire_bookings cron line
```

**Structure Decision**: Use the existing Django app and Next.js layout. Frontend work starts by reading `frontend/node_modules/next/dist/docs/`, as `frontend/AGENTS.md` requires.

## Delivery order

| Chunk | User story | Must be true before the next chunk |
|---|---|---|
| 1 | US1 Catalogue and open times | Migrations run; a guest sees correct open times |
| 2 | US2 Requests and responses | The concurrency test passes; expiry works with and without cron |
| 3 | US3 Payment and refunds | `complete_payment` refactor lands as its own commit with goods tests unedited |
| 4 | US4 Completion and earnings | The mixed goods and bookings finance test passes |

US2 must not reach production before US3. The feature launches publicly only with `009`.

## Known issue outside this feature

For goods orders, `complete_payment` ignores a successful callback that arrives after a payment has expired, so the customer's money isn't recorded anywhere. This feature fixes it for bookings only. Goods behaviour stays unchanged here, and the owner is told about it separately.

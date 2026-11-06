---

description: "Task list for service bookings"
---

# Tasks: Service Bookings

**Input**: Design documents from `specs/008-service-bookings/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/bookings-api.md, quickstart.md

**Tests**: Included, because the spec's success criteria and `quickstart.md` require them. Backend tests go through the HTTP API against real Postgres, following `backend/tests/`.

**Organization**: Tasks are grouped by user story. Deliver one phase at a time and stop for review at each checkpoint (Constitution Principle V).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task belongs to
- All paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Create the app and shared configuration

- [ ] T001 Read the relevant guides in `frontend/node_modules/next/dist/docs/` before any frontend work, as `frontend/AGENTS.md` requires, and note anything that affects the new pages in `specs/008-service-bookings/research.md`
- [ ] T002 Add `tzdata` to `backend/requirements.txt` and install it into `backend/.venv`
- [ ] T003 Create the empty `apps.bookings` app (`backend/apps/bookings/__init__.py`, `apps.py`, `models.py`, `urls.py`, `migrations/__init__.py`) and register it in `backend/config/settings.py`
- [ ] T004 Add `MARKET_TIME_ZONE = "Africa/Dar_es_Salaam"` and env-driven settings to `backend/config/settings.py`, with these defaults: `BOOKING_RESPONSE_HOURS` 12, `BOOKING_RESPONSE_BUFFER_MINUTES` 90, `BOOKING_PAYMENT_HOURS` 6, `BOOKING_PAYMENT_BUFFER_MINUTES` 60, `BOOKING_MIN_NOTICE_HOURS` 3, `BOOKING_MAX_ADVANCE_DAYS` 60, `BOOKING_SLOT_MINUTES` 30, `BOOKING_MAX_ACTIVE_UNPAID` 3, `BOOKING_CUSTOMER_CANCEL_HOURS` 24, `BOOKING_LIPA_MIN_HOURS` 3; document them in `backend/.env.example`
- [ ] T005 [P] Create `backend/tests/bookings/__init__.py` and add service, hours and booking factories to `backend/tests/factories.py`
- [ ] T006 [P] Create `frontend/src/lib/market-time.ts`, formatting dates and times with `Intl` and a fixed `timeZone: "Africa/Dar_es_Salaam"`, and test it in `frontend/src/lib/market-time.test.ts`

---

## Phase 2: Foundational

**Purpose**: Permissions and audit entries every story needs

**⚠️ CRITICAL**: Complete this before any user story

- [ ] T007 Add `bookings.view` and `bookings.manage` to `AdminPermission`, `PERMISSION_DESCRIPTIONS` and both tiers in `backend/apps/core/admin_permissions.py`; add their labels to `frontend/src/app/admin/profile/page.tsx`
- [ ] T008 Add `service.*`, `booking.*` and `refund.*` actions to `AuditAction` in `backend/apps/audit/models.py`, generate the migration, and add labels to `frontend/src/app/admin/audit-log/page.tsx`
- [ ] T009 Add `booking.created`, `booking.updated` and `refund.updated` to the event types in `frontend/src/lib/realtime.ts`, and add a `booking_audience(booking)` helper returning the customer's group, the owner's group and `ADMINS` in `backend/apps/realtime/groups.py`

**Checkpoint**: Run `python manage.py migrate` and the existing test suite. All existing tests still pass.

---

## Phase 3: User Story 1 - Provider lists services and customers find open times (Priority: P1) 🎯

**Goal**: Approved services shops publish services and hours, and anyone can see correct open times.

**Independent Test**: Follow "US1" in `quickstart.md`.

### Tests for User Story 1

> Write these first and confirm they fail.

- [ ] T010 [P] [US1] Test open times in `backend/tests/bookings/test_slots.py`: UTC+3 around midnight, multiple daily periods, closures, last start fits before closing, 3-hour notice, 60-day limit, mixed durations
- [ ] T011 [P] [US1] Test the service rules in `backend/tests/bookings/test_services_catalogue.py`: unapproved shop refused, service in goods shop refused, product in services shop refused, publishing without a location refused, wrong category kind refused, archived services hidden, other owners get 404
- [ ] T012 [P] [US1] Test shop type and categories in `backend/tests/vendors/test_shop_business_type.py` and `backend/tests/catalog/test_category_kind.py`: existing shops are GOODS, the type can't change after the request, and the default category list still returns only product categories

### Implementation for User Story 1

- [ ] T013 [US1] Add `Shop.business_type` (GOODS or SERVICES, default GOODS) and `Shop.booking_capacity` (positive integer, default 1, minimum 1) with a migration in `backend/apps/vendors/models.py`
- [ ] T014 [US1] Accept `business_type` on shop requests, make it read-only afterwards, and return both new fields from the shop serializers in `backend/apps/vendors/serializers.py` and `backend/apps/vendors/views.py`
- [ ] T015 [US1] Add `Category.kind` (PRODUCT or SERVICE, default PRODUCT; "A subcategory takes its parent's kind"; "Can't change while in use") with a migration in `backend/apps/catalog/models.py`
- [ ] T016 [US1] Make `validate_category` refuse service categories, refuse product creation in SERVICES shops, and add `kind` to the admin category serializers in `backend/apps/catalog/serializers.py`; add `?kind=` with a PRODUCT default to `CategoryListView` and extend the category delete guard in `backend/apps/catalog/views.py`
- [ ] T017 [US1] Create `Service` in `backend/apps/bookings/models.py` per `data-model.md`: `name` unique per shop, `price` "Above 0", `duration_minutes` "Multiple of the slot step; 30 to 1440", `is_published` and `is_archived` default false
- [ ] T018 [US1] Create `OpeningHours` and `ShopClosure` in `backend/apps/bookings/models.py` per `data-model.md`: `weekday` 0 to 6, `closes_at` after `opens_at`, "periods on one day can't overlap", closure `date` "Unique per shop"; generate the migration
- [ ] T019 [US1] Implement `open_slots(service, local_date, now)` in `backend/apps/bookings/slots.py`, with capacity counted through a function US2 will extend (no bookings exist yet)
- [ ] T020 [US1] Add service, schedule and closure serializers in `backend/apps/bookings/serializers.py`, with a shop-owner, APPROVED and SERVICES permission in `backend/apps/bookings/permissions.py`
- [ ] T021 [US1] Add the provider service, schedule and closure endpoints from `contracts/bookings-api.md` in `backend/apps/bookings/views.py`, with `record()` audit calls
- [ ] T022 [US1] Add the public service list, detail and slots endpoints in `backend/apps/bookings/views.py`, limited to published, unarchived services of APPROVED shops and paginated
- [ ] T023 [US1] Export the bookings URL lists in `backend/apps/bookings/urls.py` and mount them in `backend/config/urls.py`
- [ ] T024 [P] [US1] Add service, schedule and catalogue types and functions to `frontend/src/lib/api-client.ts`, and add `kind` to the category types
- [ ] T025 [US1] Add the goods or services choice to shop requests in `frontend/src/app/register/page.tsx` and `frontend/src/app/account/page.tsx`
- [ ] T026 [US1] Add the kind choice to `frontend/src/app/admin/categories/page.tsx`
- [ ] T027 [P] [US1] Create `frontend/src/app/vendor/services/page.tsx` and its new and edit pages, following `frontend/src/app/vendor/products/`
- [ ] T028 [P] [US1] Create `frontend/src/app/vendor/schedule/page.tsx` for weekly hours, closures and capacity
- [ ] T029 [P] [US1] Create `frontend/src/app/services/page.tsx`, with search and category filters and a pager
- [ ] T030 [US1] Create `frontend/src/components/booking/slot-picker.tsx` and `frontend/src/app/services/[id]/page.tsx`, labelling times in Dar es Salaam time via `lib/market-time.ts`, with booking action left for US2
- [ ] T031 [US1] Add a services section to `frontend/src/app/shops/[id]/page.tsx`, and Services links to `frontend/src/components/nav.tsx`; show service links instead of product links for services shops

**Checkpoint**: Run tests, migrations and the "US1" walkthrough in a browser. Stop for review.

---

## Phase 4: User Story 2 - Customer requests a time and the provider responds (Priority: P1)

**Goal**: Customers hold a time, providers respond, and a time can never be double booked. No money moves yet.

**Independent Test**: Follow "US2" in `quickstart.md`.

### Tests for User Story 2

> Write these first and confirm they fail.

- [ ] T032 [P] [US2] Add threaded tests in `backend/tests/bookings/test_booking_concurrency.py`, modelled on `backend/tests/orders/test_checkout_concurrency.py`: same time at capacity 1 gives one success, capacity 2 gives two, overlapping services count together
- [ ] T033 [P] [US2] Test every allowed and refused transition in `backend/tests/bookings/test_lifecycle.py`: accept, decline, customer cancel, deadlines shortened near the visit, late accept refused, unapproved shop refused
- [ ] T034 [P] [US2] Test expiry in `backend/tests/bookings/test_expiry.py`: a time frees when its deadline passes before cleanup runs, `expire_bookings` updates status, and a second run changes nothing
- [ ] T035 [P] [US2] Test access in `backend/tests/bookings/test_permissions.py`: guest, unverified email, own shop, 3 active unpaid bookings, other users get 404, and each admin tier; extend `READS` and `WRITES` in `backend/tests/core/test_admin_permissions.py`

### Implementation for User Story 2

- [ ] T036 [US2] Create `Booking` and `BookingStatusEvent` in `backend/apps/bookings/models.py` per `data-model.md`, including `contact_phone` "Required; existing phone validator", `pay_by` nullable, `payout` FK SET_NULL with `related_name="bookings"`, the four listed indexes, and `amount_due()` returning `price`; generate the migration
- [ ] T037 [US2] Add `BookingQuerySet.holding(now)` in `backend/apps/bookings/models.py`: REQUESTED with `respond_by` after now, AWAITING_PAYMENT with `pay_by` after now, and CONFIRMED (US3 adds the PENDING payment rule)
- [ ] T038 [US2] Use peak overlap of `holding(now)` against `Shop.booking_capacity` in `backend/apps/bookings/slots.py`
- [ ] T039 [US2] Implement `request_booking` in `backend/apps/bookings/services.py`: lock the shop with `select_for_update(no_key=True)`, recheck the time and 3-booking limit, set `respond_by`, freeze the price and split with `split_line()`, and write the status event in one transaction
- [ ] T040 [US2] Implement `accept_booking`, `decline_booking`, `cancel_unpaid_booking` and `expire_due_bookings` in `backend/apps/bookings/services.py`, locking the booking row, setting `pay_by` on accept, and running expiry before reads and provider actions
- [ ] T041 [US2] Create `backend/apps/bookings/management/commands/expire_bookings.py`, which prints how many bookings it changed
- [ ] T042 [US2] Add `send_booking_status_email(booking, event)` to `EmailService` and `DjangoEmailService` in `backend/apps/core/email.py`, sent on commit and best-effort
- [ ] T043 [US2] Publish `booking.created` and `booking.updated` on commit from `backend/apps/bookings/services.py`
- [ ] T044 [US2] Add the customer create, list, detail and cancel endpoints, provider list, detail, accept and decline endpoints, and admin list and detail endpoints in `backend/apps/bookings/views.py` and `serializers.py`, with querysets filtered by owner, a throttle on booking requests, and audit calls
- [ ] T045 [P] [US2] Add booking types and functions to `frontend/src/lib/api-client.ts`, and booking statuses to `STATUS_ALIASES` in `frontend/src/components/ui/pill.tsx`
- [ ] T046 [US2] Add the request form (contact phone, note, sign-in and verification prompts) to `frontend/src/app/services/[id]/page.tsx`
- [ ] T047 [P] [US2] Create `frontend/src/app/bookings/page.tsx` and `frontend/src/app/bookings/[id]/page.tsx` with status, deadlines, history, cancel and live refresh
- [ ] T048 [P] [US2] Create `frontend/src/app/vendor/bookings/page.tsx` with accept and decline, and add it to `frontend/src/components/nav.tsx`
- [ ] T049 [P] [US2] Create `frontend/src/app/admin/bookings/page.tsx` and `frontend/src/app/admin/bookings/[id]/page.tsx`, and add them to `frontend/src/components/admin-sidebar.tsx`
- [ ] T050 [US2] Make `POST /api/vendor/shops/{id}/closures` return active bookings on that date, and show them as a warning in `frontend/src/app/vendor/schedule/page.tsx`
- [ ] T051 [P] [US2] Add the `*/5` `expire_bookings` cron line next to the backup entry in `docs/deploy-contabo.md`

**Checkpoint**: Run tests and the "US2" walkthrough. Don't deploy to production until US3 is done. Stop for review.

---

## Phase 5: User Story 3 - Customer pays after acceptance, and money owed back is tracked (Priority: P1)

**Goal**: Accepted bookings can be paid and retried, and money owed back is never lost.

**Independent Test**: Follow "US3" in `quickstart.md`.

### Tests for User Story 3

> Write these first and confirm they fail.

- [ ] T052 [P] [US3] Test payments in `backend/tests/bookings/test_payments.py`: payment refused before acceptance, callback success and failure, retry, one live payment, client amount ignored, wrong amount ignored, repeated callback, Lipa Namba offered only 3 hours or more ahead, Lipa confirm and reject
- [ ] T053 [P] [US3] Test late money in `backend/tests/bookings/test_late_payments.py`: late success in each status, after `pay_by`, after the visit starts, Lipa confirmed after the visit starts, success racing the sweep, one refund entry from repeated callbacks
- [ ] T054 [P] [US3] Test cancellation and refunds in `backend/tests/bookings/test_refunds.py`: 24-hour boundary, refused within 24 hours, provider reason required, admin amount limit, payment in progress blocks cancel, mark-paid requires `finance.manage` and works once

### Implementation for User Story 3

- [ ] T055 [US3] Make `PaymentRecord.order` nullable, and add the `booking` FK with `related_name="payments"` and the `payment_has_one_target` and `one_live_payment_per_booking` constraints, with a migration, in `backend/apps/payments/models.py`
- [ ] T056 [US3] Split `complete_payment` into a shared start plus `_apply_order_outcome`, and branch `_audit_system_payment`, `_announce_payment` and `settle_manual_payment` for bookings, in `backend/apps/payments/outcomes.py`. **Commit this on its own.** All existing payment tests must pass with no edits
- [ ] T057 [US3] Exclude booking records from the Lipa Namba branch of `expire_stale_payments` in `backend/apps/payments/outcomes.py`
- [ ] T058 [US3] Add `RefundDue` per `data-model.md` in `backend/apps/payments/models.py`, with `amount` "Above 0, and no more than the payment's amount", `paid_reference` "Required when PAID", and uniqueness on `payment` and `reason`; generate the migration
- [ ] T059 [US3] Implement `on_payment_settled` in `backend/apps/bookings/services.py`: confirm only with the time held and the visit not started, otherwise create a `RefundDue`; lock the record before the booking
- [ ] T060 [US3] Add `reconcile_late_payment` and call it from `handle_azampay_callback` for a success on a booking's FAILED record, in `backend/apps/payments/outcomes.py` and `backend/apps/bookings/services.py`
- [ ] T061 [US3] Extend `holding(now)` for AWAITING_PAYMENT bookings with a PENDING payment, expire them when the visit starts, and settle stale booking payments in `expire_bookings`, in `backend/apps/bookings/models.py`, `services.py` and the command
- [ ] T062 [US3] Implement `start_booking_payment` in `backend/apps/bookings/services.py`, reusing `normalise_msisdn`, `get_mobile_money_gateway` and `azampay_amount`, with the gateway called after commit as in `_place_mobile_money_order` in `backend/apps/orders/services.py`
- [ ] T063 [US3] Implement `cancel_confirmed_booking`, provider cancel and `admin_cancel_booking` in `backend/apps/bookings/services.py`, creating `RefundDue` per the status table in `data-model.md`
- [ ] T064 [US3] Add the customer payment methods, pay and payment-status endpoints, provider cancel, and admin cancel and payment settlement endpoints, in `backend/apps/bookings/views.py`, with `AdminArea("bookings", write_permission="finance.manage")` on settlement
- [ ] T065 [US3] Add `GET /api/admin/refunds` and `POST /api/admin/refunds/{id}/mark-paid` in `backend/apps/payments/views.py` and `urls.py`, with audit and `refund.updated`, and mount them in `backend/config/urls.py`
- [ ] T066 [US3] Show a booking reference when a record has no order in `backend/apps/payments/views.py` and `frontend/src/app/dev/azampay-sandbox/page.tsx`
- [ ] T067 [P] [US3] Extract `frontend/src/components/payment/payment-method-fields.tsx` from `frontend/src/app/checkout/page.tsx`, leaving checkout unchanged in behaviour
- [ ] T068 [US3] Create `frontend/src/components/booking/booking-payment-panel.tsx` with `useLiveRefresh`, use it in `frontend/src/app/bookings/[id]/page.tsx`, and add payment functions to `frontend/src/lib/api-client.ts`
- [ ] T069 [P] [US3] Add provider cancel with a reason to `frontend/src/app/vendor/bookings/page.tsx`
- [ ] T070 [P] [US3] Add admin cancel and Lipa Namba settlement to `frontend/src/app/admin/bookings/[id]/page.tsx`
- [ ] T071 [P] [US3] Create `frontend/src/app/admin/refunds/page.tsx`, and add it to `frontend/src/components/admin-sidebar.tsx`

**Checkpoint**: Run all tests, confirm goods payment tests are unedited, and do the "US3" walkthrough with the simulator, including a goods order. Stop for review.

---

## Phase 6: User Story 4 - Provider completes the visit and earns (Priority: P2)

**Goal**: Completed visits flow into balances, payouts and reports.

**Independent Test**: Follow "US4" in `quickstart.md`.

### Tests for User Story 4

> Write these first and confirm they fail.

- [ ] T072 [P] [US4] Test completion in `backend/tests/bookings/test_completion.py`: refused before the start, completed and no-show both earn, fixed price and commission survive later changes
- [ ] T073 [P] [US4] Test finance in `backend/tests/finance/test_booking_earnings.py`: **a shop with both goods lines and bookings has exact, unmultiplied totals in every figure**, sorting by balance works, cancelled bookings add nothing, payouts claim both, failure releases both, retry works, and line counts are correct

### Implementation for User Story 4

- [ ] T074 [US4] Implement `complete_booking` and `mark_no_show` in `backend/apps/bookings/services.py`, and add the provider endpoints in `backend/apps/bookings/views.py`
- [ ] T075 [US4] Add `_available_bookings`, and claim and release bookings alongside lines, in `_claim_lines` and `_disburse` in `backend/apps/finance/services.py`
- [ ] T076 [US4] Add booking totals by the mapping in `research.md` section 9 to `shops_with_balances`, `vendor_shop_earnings`, `shop_balance` and `platform_summary` in `backend/apps/finance/services.py`, using `Subquery` on `Shop` queries and never a second join; add `booking_count`
- [ ] T077 [US4] Use `Count(..., distinct=True)` for items and bookings in `payout_queryset`, and extend `filter_transactions` with booking commission and search terms, in `backend/apps/finance/services.py`
- [ ] T078 [US4] Add `booking_id`, make `order_id` nullable, and fix `get_customer` for records with no order in `backend/apps/finance/serializers.py`; list bookings on payout details in `backend/apps/finance/views.py`
- [ ] T079 [US4] Update the transaction report and payout statement templates in `backend/apps/finance/templates/finance/reports/`, and confirm the PDFs render with booking lines
- [ ] T080 [P] [US4] Add completed and no-show actions to `frontend/src/app/vendor/bookings/page.tsx`
- [ ] T081 [P] [US4] Show bookings in `frontend/src/app/admin/transactions/page.tsx`, `frontend/src/app/admin/payouts/[id]/page.tsx` and `frontend/src/app/admin/finance/page.tsx`, updating types in `frontend/src/lib/api-client.ts`

**Checkpoint**: Run all tests and the "US4" walkthrough. Stop for review.

---

## Phase 7: Polish

**Purpose**: Whole-feature checks

- [ ] T082 [P] Add a Playwright flow from request to completion in `frontend/e2e/service-booking.spec.ts`, noting it needs the running stack
- [ ] T083 [P] Update `backend/README.md` with the bookings app, settings and command
- [ ] T084 Check for N+1 queries on booking, service and admin lists with `select_related` in `backend/apps/bookings/views.py`
- [ ] T085 Run all checks in `quickstart.md`: `pytest`, `ruff check .`, `npm run lint`, `npm run format:check`, `npm run test` and `npm run build`
- [ ] T086 Walk through all of `quickstart.md` in a browser, record the results in `specs/008-service-bookings/quickstart.md`, and tell the owner about the late-callback gap in goods orders noted in `plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all stories
- **US1 (Phase 3)**: Depends on Foundational
- **US2 (Phase 4)**: Depends on US1, because it needs services and open times
- **US3 (Phase 5)**: Depends on US2, because it needs accepted bookings
- **US4 (Phase 6)**: Depends on US3, because earnings need paid bookings
- **Polish (Phase 7)**: Depends on all stories

### Within Each User Story

- Tests are written first and must fail before implementation
- Models, then services, then endpoints, then frontend
- Migrations run against Postgres before the checkpoint

### Parallel Opportunities

- Test tasks marked [P] within a story
- Frontend pages marked [P], once that story's API client task is done
- T005 and T006 in Setup

---

## Parallel Example: User Story 2

```text
Task: "Add threaded tests in backend/tests/bookings/test_booking_concurrency.py"
Task: "Test every allowed and refused transition in backend/tests/bookings/test_lifecycle.py"
Task: "Test expiry in backend/tests/bookings/test_expiry.py"
Task: "Test access in backend/tests/bookings/test_permissions.py"
```

---

## Implementation Strategy

### Incremental Delivery

1. Setup and Foundational: migrations run, existing tests pass.
2. US1: providers can list services and the public can see open times. This can ship without bookings if the owner wants.
3. US2 and US3: these reach production together, because accepted bookings can't be paid without US3.
4. US4: providers get paid.
5. Public launch waits for rides (`009`).

Stop for the owner's review at each checkpoint. Don't run all phases in one unattended pass.

---

## Notes

- Tick tasks off as they finish, and check them against the code rather than trusting the boxes.
- The `complete_payment` refactor (T056) is a separate commit, so a goods regression is easy to find and revert.
- Commit or push only when the owner asks.

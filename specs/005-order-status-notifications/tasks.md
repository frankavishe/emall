---

description: "Task list template for feature implementation"
---

# Tasks: Order Status Notifications

**Input**: Design documents from `/specs/005-order-status-notifications/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/order-status-notification-email.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context commits this feature to `pytest` +
`pytest-django`, asserting against `django.core.mail.outbox` under the existing console/locmem
email backend — the same testing commitment 001–004 already made, applied to the notification
side effect this feature adds. FR-003/FR-005 (no notification on rejection; delivery failure never
blocks the transition) are mechanism-level guarantees, so their tests live in the Foundational
phase rather than any one user story.

**Organization**: Tasks are grouped by user story (P1–P3 from spec.md) to enable independent
implementation and testing of each story. Because this feature's entire implementation is one
small, shared choke point (a single `EmailService` method plus a single `transaction.on_commit()`
hook — research.md §1–§3), that shared mechanism and *all four* status-content branches are built
once in the Foundational phase; each user-story phase then adds the tests that prove *its specific*
status/statuses produce the right email, per Constitution Principle V's staged, reviewed delivery.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Paths follow `plan.md`'s Project Structure: this feature adds no new Django app and touches no
  frontend file — all work is in `backend/apps/core/email.py`, `backend/apps/orders/services.py`,
  and `backend/tests/orders/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

No tasks — this feature adds no new Django app, no new dependency, and no migration (plan.md
Technical Context, data-model.md: no schema change). Foundational work begins directly below.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the one shared mechanism every user story's tests exercise: the new
`EmailService`/`DjangoEmailService` method covering all four status variants, and the
`transaction.on_commit()` hook in `advance_order_item_status()` that calls it after a successful
transition, isolated from failures.

**⚠️ CRITICAL**: No user story's tests can pass until this phase is complete — every story asserts
against the same `send_order_item_status_email()` method and the same hook.

- [X] T001 Add abstract method `send_order_item_status_email(self, order_item)` to `EmailService`
      in `backend/apps/core/email.py`, and implement it on `DjangoEmailService` using
      `django.core.mail.send_mail` in the same plain-text style as
      `send_verification_email`/`send_password_reset_email`. Per
      contracts/order-status-notification-email.md, branch on `order_item.status` and use exactly
      this subject/body-states mapping (recipient is `order_item.order.customer.email`; body must
      also name `order_item.order_id` and `order_item.product.name` in every branch):
      - `PROCESSING` → subject `"Your order is being prepared"`, body states "being prepared"
      - `SHIPPED` → subject `"Your order has shipped"`, body states "has shipped"
      - `DELIVERED` → subject `"Your order has been delivered"`, body states "has been delivered"
      - `CANCELLED` → subject `"An item in your order was cancelled"`, body states "was cancelled"
        and MUST NOT mention refund, payment, or charge in any form (FR-008)
- [X] T002 In `backend/apps/orders/services.py`, add a module-level helper
      `_notify_order_item_status_change(order_item)` that calls
      `apps.core.email.get_email_service().send_order_item_status_email(order_item)` inside a
      `try`/`except Exception` block, logging the exception via
      `logging.getLogger(__name__).exception(...)` on failure and never re-raising (research.md
      §2). In `advance_order_item_status()`, immediately after the existing
      `OrderItemStatusEvent.objects.create(order_item=order_item, status=new_status)` line (still
      inside the existing `with transaction.atomic():` block), add
      `transaction.on_commit(lambda: _notify_order_item_status_change(order_item))` so the
      notification only fires once the transition has actually committed (depends on T001)
- [X] T003 [P] Add `backend/tests/orders/test_status_notification_mechanism.py`: (a) attempt an
      invalid transition (e.g. `DELIVERED` → `PROCESSING`) via `advance_order_item_status()`,
      assert it raises `TransitionError` and `django.core.mail.outbox` stays empty (FR-003, SC-002
      — no notification on a rejected transition); (b) monkeypatch
      `apps.orders.services.get_email_service` to return a stub whose
      `send_order_item_status_email` raises, perform a valid transition (e.g. `PENDING` →
      `PROCESSING`), and assert the call still returns normally with `order_item.status` persisted
      as the new value in the database, and that no exception propagates out of
      `advance_order_item_status()` (FR-005, SC-004 — delivery failure never blocks or rolls back
      the transition) (depends on T002)

**Checkpoint**: The notification mechanism exists and is proven not to fire on rejection nor to be
able to block a real transition on failure. User story test-writing can now begin.

---

## Phase 3: User Story 1 - Customer is emailed when their item ships or is delivered (Priority: P1) 🎯 MVP

**Goal**: Prove that advancing an `OrderItem` to `SHIPPED` or `DELIVERED` sends the Customer
exactly one correctly-addressed, correctly-worded email per transition, scoped to that one line
item even when an order has lines from multiple vendors.

**Independent Test**: Place a test order, advance one of its lines `PENDING` → `PROCESSING` →
`SHIPPED` → `DELIVERED` via the existing `PATCH /api/vendor/order-items/{id}/status/` endpoint (or
`advance_order_item_status()` directly), and confirm one email appears in the outbox after the
`SHIPPED` call and a second, separate one after the `DELIVERED` call, each naming the correct order
and product.

### Tests for User Story 1

> **NOTE**: These tests exercise the Foundational-phase implementation (T001, T002); they fail
> before it exists and pass once it does.

- [X] T004 [P] [US1] Add `backend/tests/orders/test_status_notification_shipped_delivered.py`:
      advance an `OrderItem` to `SHIPPED`, assert exactly one email in
      `django.core.mail.outbox` addressed to the order's customer, subject `"Your order has
      shipped"`, body containing the order id and the product's name; then advance the same item
      to `DELIVERED`, assert a second, separate email with subject `"Your order has been
      delivered"` — total of two emails, never a combined summary (FR-002, FR-004, Acceptance
      Scenarios 1–2, SC-001)
- [X] T005 [P] [US1] In the same file, add a test for Acceptance Scenario 3: build one `Order`
      with two `OrderItem`s whose products belong to two different vendors' shops; advance each
      item's status independently (e.g. one to `SHIPPED`, the other to `DELIVERED`); assert two
      separate emails are sent, each mentioning only its own item's product — never a
      whole-order summary mixing both items

**Checkpoint**: User Story 1 is independently verifiable — its tests pass standalone against the
Foundational implementation.

---

## Phase 4: User Story 2 - Customer is emailed when their item is cancelled (Priority: P2)

**Goal**: Prove that advancing an `OrderItem` to `CANCELLED` sends a correctly-worded email that
never states or implies a refund/payment outcome.

**Independent Test**: Advance an `OrderItem` from `PENDING` (or `PROCESSING`) to `CANCELLED`, and
confirm one email appears in the outbox with the cancellation subject/body and no refund/payment
language.

### Tests for User Story 2

- [X] T006 [P] [US2] Add `backend/tests/orders/test_status_notification_cancelled.py`: advance an
      `OrderItem` to `CANCELLED`, assert exactly one email in the outbox addressed to the order's
      customer, subject `"An item in your order was cancelled"`, body containing the order id and
      product name, and assert the body does **not** contain any of `"refund"`, `"charge"`,
      `"payment"` (case-insensitive) (FR-008, Acceptance Scenarios 1–2)

**Checkpoint**: User Stories 1 and 2 are both independently verifiable.

---

## Phase 5: User Story 3 - Customer is emailed when their item enters processing (Priority: P3)

**Goal**: Prove that advancing an `OrderItem` to `PROCESSING` sends a correctly-worded confirmation
email.

**Independent Test**: Advance an `OrderItem` from `PENDING` to `PROCESSING`, and confirm one email
appears in the outbox with the processing subject/body.

### Tests for User Story 3

- [X] T007 [P] [US3] Add `backend/tests/orders/test_status_notification_processing.py`: advance an
      `OrderItem` from `PENDING` to `PROCESSING`, assert exactly one email in the outbox addressed
      to the order's customer, subject `"Your order is being prepared"`, body containing the order
      id and product name (Acceptance Scenario 1)

**Checkpoint**: All three user stories are independently verifiable; the full notification surface
described in the spec is covered by tests.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verify the whole feature for real, per Constitution Principle V, and close out
documentation/security review

- [X] T008 Run the full backend test suite (`pytest`) against the real `emall-postgres` container
      and confirm zero regressions in addition to all new tests from T003–T007 passing
- [X] T009 Run `specs/005-order-status-notifications/quickstart.md` Scenarios 1–5 for real against
      a running `runserver` with the console `EMAIL_BACKEND`, confirming the printed emails match
      each scenario's expectations (Scenario 6 is already covered by the automated test in T003)
- [X] T010 [P] Add a short "Order Status Notifications" section to `backend/README.md`, mirroring
      the existing verification/password-reset email section: note that Vendor status updates now
      trigger a Customer email via the same console/SMTP-swappable `EMAIL_BACKEND`, and that
      delivery failures are logged, not raised (FR-005)
- [X] T011 [P] Security/content review pass (Constitution Principle III): confirm no payment
      method, card, or transaction-reference data is ever read or included in any notification
      email (grep `backend/apps/core/email.py`'s new method and `backend/apps/orders/services.py`
      for any `payment`/`PaymentRecord` reference — expect none), and confirm the T002 failure log
      line does not log the customer's raw email address at a log level that would be captured in
      any committed file

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks.
- **Foundational (Phase 2)**: No dependency on Setup (skipped) — BLOCKS all user stories (T001 →
  T002 → T003, strictly sequential: T002 needs T001's method to call, T003 needs T002's hook to
  test).
- **User Stories (Phase 3–5)**: All depend on Foundational (T001–T003) completion. Once
  Foundational is done, US1/US2/US3's test files are fully independent of each other (different
  files, no shared fixtures beyond factories already used across the existing `tests/orders/`
  suite) and may be written/run in any order or in parallel.
- **Polish (Phase 6)**: Depends on all desired user stories being complete (T008 in particular
  wants T003–T007 all present to count them in the "zero regressions" run).

### Within Each Phase

- T001 before T002 (T002 calls the method T001 adds).
- T002 before T003 (T003 tests the hook T002 adds).
- T004 and T005 can run in parallel (same file is fine since they're independent test functions,
  but no other task writes that file).
- T006, T007 each independent of T004/T005 and of each other.

### Parallel Opportunities

- T004 and T005 (both [US1], same new file, independent test functions) can be written together.
- T006 [US2] and T007 [US3] can be written in parallel with each other and with T004/T005, once
  Foundational (T001–T003) is complete.
- T010 and T011 (Polish) can run in parallel with each other; both should follow T008/T009.

---

## Parallel Example: User Stories 1–3 (after Foundational)

```bash
# Once T001-T003 are complete, all three stories' test files are independent:
Task: "Add tests/orders/test_status_notification_shipped_delivered.py (T004, T005) [US1]"
Task: "Add tests/orders/test_status_notification_cancelled.py (T006) [US2]"
Task: "Add tests/orders/test_status_notification_processing.py (T007) [US3]"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001–T003) — this alone already implements *all four* status
   branches (the mechanism doesn't split by story), so nothing further is needed to make US1's
   behavior actually work.
2. Complete Phase 3: User Story 1 tests (T004, T005) to prove it.
3. **STOP and VALIDATE**: run T004/T005, then quickstart.md Scenario 1, for real.
4. This is already a deployable MVP — Customers get shipped/delivered emails — even though
   CANCELLED/PROCESSING emails are *also* already firing in production once Foundational lands
   (there is no way to ship the mechanism partially, per research.md §1's single-choke-point
   design). US2/US3 exist to formally verify and document that the other two statuses work too.

### Incremental Delivery

1. Foundational (T001–T003) → mechanism proven safe (no notification on rejection, failure
   isolation).
2. US1 tests (T004–T005) → shipped/delivered path formally verified → review/demo.
3. US2 test (T006) → cancelled path formally verified → review/demo.
4. US3 test (T007) → processing path formally verified → review/demo.
5. Polish (T008–T011) → full-suite regression run, quickstart walkthrough, docs, security review.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Unlike a typical feature, the "implementation" here is entirely inside Phase 2 (Foundational) —
  each user-story phase is tests-only, because the spec's four statuses are handled by one shared
  method and one shared hook (research.md §1, §3), not by per-story code paths. This was a
  deliberate simplicity call (Constitution Principle VI), not an omission.
- Commit after each task or logical group.
- Stop at any checkpoint to validate independently.

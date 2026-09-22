# Research: Order Status Notifications

No `NEEDS CLARIFICATION` markers were left in the Technical Context — this feature is additive to
existing, already-decided infrastructure (Django/DRF backend, `apps.core.email` swappable email
service, `apps.orders.services.advance_order_item_status()`). The decisions below are the concrete
design choices needed to satisfy the spec's requirements within that existing infrastructure.

## 1. Where to trigger the notification

**Decision**: Trigger inside `apps.orders.services.advance_order_item_status()` itself, registered
via `django.db.transaction.on_commit()` rather than sent inline inside the existing
`transaction.atomic()` block.

**Rationale**:
- `advance_order_item_status()`'s own docstring already states it is "the only path that ever
  changes `OrderItem.status`" — hooking the notification here is the single choke point that
  satisfies FR-004 (exactly one notification per transition) without relying on every current and
  future call site (currently only `VendorOrderItemStatusUpdateView`) to remember to send it.
- `transaction.on_commit()` defers the callback until the enclosing atomic block actually commits.
  This directly satisfies FR-005/SC-004: if the transition itself fails/rolls back (e.g. the
  `TransitionError` raised before any write, or a DB error), the callback never runs at all — there
  is no risk of notifying about a change that didn't happen. Conversely, once the transition has
  committed, a notification-delivery failure cannot reach back and undo it, because the commit has
  already happened.
- Sending inline inside the `atomic()` block was rejected: an email-transport exception raised
  there would abort the whole transaction, incorrectly rolling back a real, valid status change
  (and, for CANCELLED, the stock restoration) just because notification delivery failed — the
  opposite of FR-005.

## 2. Isolating notification failures from the request/response cycle

**Decision**: Wrap the `on_commit`-scheduled call in a `try`/`except Exception` that logs (via
Python's standard `logging` module, a new but minimal addition — no logging framework exists in
this codebase yet) and swallows the error, rather than letting it propagate.

**Rationale**: `on_commit()` callbacks still run synchronously within the same request before the
response is returned. An uncaught exception there would turn into a 500 response even though the
underlying status transition already committed successfully — silently contradicting the "MUST
NOT block" language of FR-005 from the client's point of view. A minimal `logger.exception(...)`
call preserves debuggability without requiring a new task queue or retry mechanism, which is out of
scope for this feature's stated scale (learning-project MVP, matching 001–004's scale/scope).

**Alternatives considered**: A background task queue (Celery/RQ) for guaranteed-delivery retries —
rejected as disproportionate infrastructure for an MVP where the existing email transport (Django's
`send_mail`) is itself already a mocked/swappable edge per Constitution Principle IV, not a
guaranteed-delivery system.

## 3. Shape of the new email-service method(s)

**Decision**: Add one new method, `send_order_item_status_email(self, order_item)`, to the existing
`EmailService` abstract base class and its `DjangoEmailService` implementation in
`apps/core/email.py`, alongside the existing `send_verification_email`/`send_password_reset_email`.
The method reads `order_item.status` internally and branches subject/body text per status
(PROCESSING/SHIPPED/DELIVERED/CANCELLED).

**Rationale**: FR-007 requires reusing the existing mechanism rather than building a parallel one —
adding a method to the same class is the smallest change that satisfies this. A single method
keyed on the order item (rather than four near-duplicate `send_..._email` methods, one per status)
avoids reintroducing the same subject/body scaffolding four times for what is conceptually one
notification type with four variants; each variant's copy is a few lines in a single `if`/`elif`
chain, well within Constitution Principle VI's "prefer the simplest implementation" default (this
isn't one of the three structural elements the constitution protects from simplification).

**Alternatives considered**: Four separate abstract methods (`send_order_processing_email`,
`send_order_shipped_email`, etc.) — rejected as unnecessary interface surface for what the spec
(FR-002) treats as one notification concept ("identify the order/item and the new status reached"),
not four independent features.

## 4. Recipient and content

**Decision**: Recipient is always `order_item.order.customer` (the existing FK chain from
003-cart-checkout), notified at `customer.email` regardless of `is_email_verified` (per spec
Assumptions — this isn't a security-sensitive action). Content includes the order's id, the
product's name (`order_item.product.name`), and the new status, in the same plain-text style as
the existing verification/reset emails (no HTML templates — matches spec Assumptions).

**Rationale**: `order_item.order.customer` and `order_item.product` are both already-loaded FK
relationships on `OrderItem` (data already exists from 003-cart-checkout); no new fields or queries
are needed beyond following existing relations, keeping this feature purely additive.

## 5. Cancellation wording (FR-008)

**Decision**: The CANCELLED-status email body states the item was cancelled and, if the customer
has questions, to contact support — it does not mention refunds, charges, or payment status in
either direction.

**Rationale**: Directly satisfies FR-008 and the spec's Edge Cases note that payment/refund
handling for cancellations remains out of scope (per 004-order-fulfillment's own Assumptions,
unchanged by this feature).

## 6. Testing approach

**Decision**: Backend contract/unit tests use Django's test `EMAIL_BACKEND` (`locmem`, already the
implicit default in test settings via `pytest-django`) and assert against `django.core.mail.outbox`
— the same mechanism already implicitly available for 001-accounts-auth's verification/reset email
tests, requiring no new test infrastructure.

**Rationale**: Matches the existing project testing pattern (`pytest` + `pytest-django`, real
Postgres for data, no new mocking framework) with zero new dependencies.

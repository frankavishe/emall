# Implementation Plan: Order Status Notifications

**Branch**: `005-order-status-notifications` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-order-status-notifications/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Email the Customer who placed an order whenever a Vendor advances one of that order's line items
to `PROCESSING`, `SHIPPED`, `DELIVERED`, or `CANCELLED` — closing the gap 003-cart-checkout and
004-order-fulfillment both explicitly deferred ("notification delivery is a separate future
feature"). No new entity, endpoint, or request/response shape is introduced: the single existing
choke point that changes `OrderItem.status` — `apps.orders.services.advance_order_item_status()`
— schedules the send via `transaction.on_commit()` after a successful transition, calling one new
method (`send_order_item_status_email`) added to the existing swappable
`apps.core.email.EmailService` abstraction already used for verification/password-reset email
(Constitution Principle IV). A delivery failure is caught and logged at the call site so it can
never roll back or block the already-committed status change (FR-005). No frontend work — nothing
in the UI changes; the email is the entire user-visible surface of this feature.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x — existing). No frontend changes.

**Primary Dependencies**: Django (`django.core.mail`, `django.db.transaction.on_commit`) — both
already in use, existing. Python's standard `logging` module is newly introduced at this one call
site (no logging framework existed in this codebase before; research.md §2) to isolate delivery
failures from the request/response cycle. No new third-party packages.

**Storage**: PostgreSQL — no schema change, no migration. This feature reads existing `Order`/
`OrderItem`/`User` columns and writes nothing new (data-model.md).

**Testing**: `pytest` + `pytest-django` (existing pattern). Backend contract/unit tests assert
against `django.core.mail.outbox` under Django's `locmem`/console test email backend (already
implicitly available, no new test infrastructure — research.md §6): one email sent per valid
transition with correct recipient/subject/content per status, zero emails sent on a rejected
transition, and a forced-failure test proving a raised exception from the email service does not
propagate into the HTTP response or roll back the persisted status change.

**Target Platform**: Linux server (existing Django deployment target). No frontend/browser surface
for this feature — nothing to validate in a browser beyond the console-printed email in dev.

**Project Type**: Web application (existing `backend/` + `frontend/` split). This feature is
backend-only: it extends the existing `backend/apps/orders/` and `backend/apps/core/` apps — no new
Django app (per Constitution's fixed app list) and no `frontend/` changes at all.

**Performance Goals**: No feature-specific throughput target; sending one additional email per
status transition is negligible next to the existing DB write in the same request.

**Constraints**: Exactly one notification per successful transition, never for a rejected one
(FR-003, FR-004) — satisfied structurally by hooking the single existing transition function
rather than call sites. Notification delivery MUST be decoupled from the transition's atomicity
(FR-005) — satisfied by `transaction.on_commit()` plus a caught/logged exception at the callback,
never inside the existing `transaction.atomic()` block.

**Scale/Scope**: Learning-project MVP scale, same as 001–004. No pagination/throughput concerns —
this feature adds no list endpoint, just a side effect on an existing single-object mutation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | This feature adds no new endpoint, role check, or client-facing permission surface — it reuses `PATCH /api/vendor/order-items/{id}/status/`'s existing `IsOrderItemShopOwner`/shop-approval enforcement unchanged | **PASS / N/A** — nothing new to authorize; the recipient (Customer) is derived server-side from `order_item.order.customer`, never client-supplied |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | Not implicated — this feature doesn't change who can mutate fulfillment status, only what happens (an email) after an already-gated mutation succeeds | **PASS / N/A** |
| III. Data & Payment Security | Cancellation notifications MUST NOT state or imply a refund/payment outcome (FR-008) | **PASS** — contracts/order-status-notification-email.md fixes the CANCELLED copy to omit refund/payment language; no payment field is read or written by this feature |
| IV. Real Core, Mocked Edges | Outbound email is explicitly a mocked/swappable edge, not core correctness; the core correctness this feature must get right is *not* interfering with the real `advance_order_item_status()` transition | **PASS** — new method added to the existing swappable `EmailService`/`DjangoEmailService` pair (no parallel transport introduced, FR-007); the status transition itself (core) is untouched logic, only observed via `on_commit` |
| V. Spec-Driven, Staged Delivery | Plan defers implementation to `/speckit-tasks` + `/speckit-implement`, in reviewable per-user-story chunks | **PASS** — no code written in this phase; `/speckit-tasks` will order by User Story 1 (P1, shipped/delivered) → User Story 2 (P2, cancelled) → User Story 3 (P3, processing), per spec priorities |
| VI. Simplicity Within a Load-Bearing Domain Model | Must not introduce a new persisted "Notification" entity or new role/state machine beyond what's needed | **PASS** — data-model.md deliberately adds zero tables; this feature doesn't touch any of the three protected structural elements (role model, shop approval state machine, per-line-item fulfillment status) — it only observes the third one, never modifies it |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: research.md's decisions (hook the single existing `advance_order_item_
status()` choke point via `transaction.on_commit()`, one new `EmailService` method rather than
four, no persisted notification record, CANCELLED copy excluding refund/payment language) were
made specifically to satisfy the gates above, not around them — all six gates still **PASS** after
design.

## Project Structure

### Documentation (this feature)

```text
specs/005-order-status-notifications/
├── plan.md                # This file (/speckit-plan command output)
├── research.md            # Phase 0 output (/speckit-plan command)
├── data-model.md          # Phase 1 output (/speckit-plan command)
├── quickstart.md          # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── order-status-notification-email.md
├── checklists/
│   └── requirements.md    # already exists (spec quality checklist)
└── tasks.md                # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── core/
│   │   └── email.py               # extended — new EmailService.send_order_item_status_email()
│   │                               #   abstract method + DjangoEmailService implementation
│   │                               #   (subject/body branching by status, research.md §3)
│   ├── accounts/                  # existing — no changes (User.email/is_email_verified read only)
│   ├── vendors/                   # existing — no changes
│   ├── catalog/                   # existing — no changes (Product.name read only)
│   ├── cart/                      # existing — no changes
│   ├── payments/                  # existing — no changes (cancellation email excludes payment info)
│   └── orders/                    # extended — no new app
│       └── services.py            # extended — advance_order_item_status() schedules
│                                   #   transaction.on_commit(lambda: get_email_service()
│                                   #   .send_order_item_status_email(order_item)) after a
│                                   #   successful transition, wrapped to catch+log failures
│                                   #   (research.md §1, §2); no other function in this file changes
└── tests/
    ├── core/                      # extended — email content per status, one call per send
    └── orders/                    # extended — one email per valid transition (recipient/content),
                                    #   zero emails on a rejected transition, delivery-failure
                                    #   isolation (status persists + 200 despite a forced raise)

frontend/                          # NO CHANGES — this feature has no UI surface
```

**Structure Decision**: Option 2 (web application), continuing the existing `backend/` Django +
`frontend/` Next.js split — but this feature touches `backend/` only. It extends two existing apps
(`apps.core` for the email method, `apps.orders` for the trigger point) with no new Django app and
no new Next.js routes, since the entire feature is an invisible-to-the-UI side effect.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

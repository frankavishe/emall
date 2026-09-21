---

description: "Task list template for feature implementation"
---

# Tasks: Vendor Order Fulfillment

**Input**: Design documents from `/specs/004-order-fulfillment/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/order-fulfillment-api.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context commits this feature to `pytest` +
`pytest-django` + `factory_boy` + DRF `APIClient`, calling out transition-matrix rejection
(FR-003, SC-002), cross-vendor isolation (FR-004), and stock-restoration atomicity (FR-011) as the
highest-value test targets — this is the same testing commitment 001–003 already made, applied to
the transition/cancellation logic this feature adds.

**Organization**: Tasks are grouped by user story (P1–P3 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Paths follow `plan.md`'s Project Structure: this feature adds no new Django app — all backend
  work is in `backend/apps/orders/`, `backend/tests/orders/`; frontend work is in
  `frontend/src/app/{vendor/orders,admin/orders}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

No tasks — this feature adds no new Django app and no new dependency (plan.md Technical Context,
research.md §6: fulfillment status is order-line domain logic and stays inside the existing
`apps/orders`). Foundational work begins directly below.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Widen the `OrderItem` status model, add the history table, and implement the one
service function every mutating endpoint calls

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — User Story 1's
status-update endpoint, User Story 2's displayed values, and User Story 3's history view all read
or write through this shared model/service layer

- [X] T001 Widen `OrderItem.Status` in `backend/apps/orders/models.py`: add `PROCESSING =
      "PROCESSING", "Processing"`, `SHIPPED = "SHIPPED", "Shipped"`, `DELIVERED = "DELIVERED",
      "Delivered"`, `CANCELLED = "CANCELLED", "Cancelled"` to the existing `Status` class
      (currently only `PENDING = "PENDING", "Pending"`) per data-model.md; default stays `PENDING`
- [X] T002 [P] Create `OrderItemStatusEvent` model in `backend/apps/orders/models.py` per
      data-model.md: `order_item` (`ForeignKey(OrderItem, related_name="status_events",
      on_delete=CASCADE)`), `status` (`CharField`, `choices=OrderItem.Status`), `changed_at`
      (`auto_now_add=True`) (depends on T001)
- [X] T003 Generate and apply the `orders` migration (`python manage.py makemigrations orders &&
      python manage.py migrate`) (depends on T001, T002)
- [X] T004 Implement `advance_order_item_status(order_item, new_status)` in
      `backend/apps/orders/services.py`: validate the requested transition against the fixed
      adjacency map `PENDING→{PROCESSING, CANCELLED}`, `PROCESSING→{SHIPPED, CANCELLED}`,
      `SHIPPED→{DELIVERED}`, `DELIVERED→{}`, `CANCELLED→{}` (FR-002, FR-003, research.md §1);
      raise a typed `TransitionError` (mirroring `CheckoutError`) for any other requested pair,
      writing nothing. On a valid transition to `CANCELLED`: inside one `transaction.atomic()`
      block, `select_for_update()` the line's `product` row, increment
      `product.stock_quantity` by `order_item.quantity` (FR-011, research.md §2), save the new
      `status`, and create one `OrderItemStatusEvent(order_item=order_item, status=new_status)`
      row (FR-009). On any other valid transition: same atomic save + history-event creation,
      without the stock step (depends on T001, T002, T003)
- [X] T005 [P] Create `backend/apps/orders/permissions.py` with `IsOrderItemShopOwner`
      (object-level: `obj.product.shop.owner_id == request.user.id`), mirroring
      `apps.catalog.permissions.IsProductOwner` (research.md §5) (depends on T001)

**Checkpoint**: `OrderItem.Status` widened, `OrderItemStatusEvent` schema and
`advance_order_item_status()` exist. User story implementation can now begin.

---

## Phase 3: User Story 1 - Vendor views and fulfills their own order lines (Priority: P1) 🎯 MVP

**Goal**: A Vendor can see the order line items belonging to their own shop's products across all
Customers' orders, and advance each one through PENDING → PROCESSING → SHIPPED → DELIVERED (or to
CANCELLED from PENDING/PROCESSING), independently of other vendors' lines on the same order.

**Independent Test**: As a Vendor with an APPROVED shop, place a test order (as a Customer)
containing one of that Vendor's products, log in as the Vendor, confirm the line appears in
`GET /api/vendor/order-items`, and advance it through the lifecycle one step at a time via
`PATCH .../status`.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T006 [P] [US1] Contract test `GET /api/vendor/order-items` — returns only lines whose
      product belongs to the requester's own shop(s), across every Customer's order, paginated,
      each row including shipping details; `403` for a non-Vendor caller (FR-001, FR-004,
      Acceptance Scenario 1) in `backend/tests/orders/test_vendor_order_item_list.py`
- [X] T007 [P] [US1] Contract test `PATCH /api/vendor/order-items/{id}/status` — `200` for each
      single valid forward step `PENDING→PROCESSING→SHIPPED→DELIVERED` (FR-002, FR-003,
      Acceptance Scenario 2/3) in
      `backend/tests/orders/test_vendor_order_item_status_transitions.py`
- [X] T008 [P] [US1] Contract test `PATCH .../status` rejections — `400` with the stored status
      unchanged for a backward transition, a skipped transition, a transition attempted from
      `DELIVERED` or `CANCELLED`, and `CANCELLED` attempted from `SHIPPED` (FR-003, Edge Cases,
      SC-002) in `backend/tests/orders/test_vendor_order_item_invalid_transitions.py`
- [X] T009 [P] [US1] Contract test cross-vendor isolation — `PATCH .../status` on another vendor's
      line ID returns `404` with no detail leaked; `PATCH .../status` on the requester's own line
      whose shop is not currently `APPROVED` returns `403` (FR-004, FR-010, Acceptance Scenario 5);
      additionally, on a multi-vendor order, confirm that Vendor A advancing their own line leaves
      Vendor B's line on the same order completely unchanged — same `status`, same
      `OrderItemStatusEvent` count, via `GET /api/vendor/order-items/` as Vendor B before and after
      (FR-004, SC-004, Acceptance Scenario 4) in
      `backend/tests/orders/test_vendor_order_item_isolation.py`
- [X] T010 [P] [US1] Contract test stock restoration — cancelling a `quantity: 2` line increases
      the product's `stock_quantity` by exactly `2` (FR-011, SC-006); a concurrency test mirroring
      `test_checkout_concurrency.py`'s pattern confirms two concurrent cancellations of different
      lines for the same product both restore correctly with no lost update
      in `backend/tests/orders/test_vendor_order_item_cancel_stock.py`

### Implementation for User Story 1

- [X] T011 [US1] Implement `VendorOrderItemSerializer` (id, `order_id`, `product` [id, name],
      `quantity`, `unit_price`, `status`, nested `shipping` denormalized from `order_item.order`
      — no `status_history` field, research.md §4) and `OrderItemStatusUpdateSerializer` (single
      `status` field, a `ChoiceField` restricted to `{PROCESSING, SHIPPED, DELIVERED, CANCELLED}`
      — a Vendor can never request `PENDING`) in `backend/apps/orders/serializers.py` (depends on
      T001)
- [X] T012 [US1] Implement `VendorOrderItemListView` in `backend/apps/orders/views.py`: `IsVendor`;
      queryset `OrderItem.objects.filter(product__shop__owner=request.user)
      .select_related("product", "product__shop", "order")` to avoid N+1 across the denormalized
      shipping/product fields (Constitution Resource Utilization) (depends on T011)
- [X] T013 [US1] Implement `VendorOrderItemStatusUpdateView` in `backend/apps/orders/views.py`:
      `IsVendor`; `get_object_or_404(OrderItem, pk=item_id, product__shop__owner=request.user)`
      (404 for cross-vendor, FR-004); if `order_item.product.shop.status != Shop.Status.APPROVED`
      raise `PermissionDenied` (403, FR-010); else validate via
      `OrderItemStatusUpdateSerializer`, call `advance_order_item_status()` (T004), translate a
      `TransitionError` to `400 {"status": [str(error)]}` (depends on T011, T004; same file as
      T012)
- [X] T014 [US1] Wire `vendor_urlpatterns` (`vendor/order-items`,
      `vendor/order-items/<int:item_id>/status`) in `backend/apps/orders/urls.py`; include at
      `api/vendor/` in `backend/config/urls.py` alongside the existing
      `apps.vendors.urls`/`apps.catalog.urls` vendor includes (depends on T012, T013)
- [X] T015 [US1] Add `listVendorOrderItems(page)`/`updateOrderItemStatus(itemId, status)` calls to
      `frontend/src/lib/api-client.ts`, matching the `checkout`/`listOrders`/`getOrder`
      wrapper-function precedent already in that file (depends on T014)
- [X] T016 [US1] Build `frontend/src/app/vendor/orders/page.tsx`: lists the Vendor's own order
      lines with current status and shipping context, and an action control constrained to the
      line's valid next step(s) (advance or cancel), server-validated regardless (depends on T015)

**Checkpoint**: User Story 1 is fully functional and independently testable — a Vendor can see and
fulfill their own order lines end to end, backend and frontend.

---

## Phase 4: User Story 2 - Customer sees fulfillment progress on their order (Priority: P1)

**Goal**: A Customer sees each line item's current fulfillment status on their existing order
detail page, updated as the owning Vendor advances it.

**Independent Test**: As a Customer with a placed order, open `GET /api/orders/{id}` (and the
`/orders/{id}` page) and confirm each line shows its current status; re-check after a Vendor
advances a line and confirm the new value appears with no other change.

> research.md §7 found `OrderItemSerializer` (003-cart-checkout) already returns `status` per line
> and `frontend/src/app/orders/[id]/page.tsx` already renders `item.status` — widening
> `OrderItem.Status` (T001) is expected to be sufficient on its own. This phase's job is to prove
> that with a regression test and a live check, not to write new display code.

### Tests for User Story 2 ⚠️

- [X] T017 [US2] Regression contract test: after a Vendor advances a line past `PENDING` (via
      `advance_order_item_status()`), `GET /api/orders/{id}` (existing 003-cart-checkout endpoint,
      unchanged) reflects the new value (`PROCESSING`/`SHIPPED`/`DELIVERED`/`CANCELLED`) on that
      line with no other field changed (FR-005, research.md §7) in
      `backend/tests/orders/test_order_detail_fulfillment_status.py`
- [X] T018 [US2] Regression contract test: no verb on `/api/orders/{id}` accepts a status-changing
      request from a Customer — `PATCH`/`POST`/`DELETE` on that path are all rejected (`404`/`405`,
      the endpoint only ever defined `GET`) (FR-006) in the same file as T017

### Implementation for User Story 2

- [X] T019 [US2] Manually load `/orders/{id}` in the browser for an order with a line past
      `PENDING` and confirm `frontend/src/app/orders/[id]/page.tsx` renders the new status
      correctly with no code change (quickstart.md Scenario 2); if an unfamiliar status string
      breaks the existing badge/text rendering, apply the minimal fix in that file (depends on
      T001, T017)

**Checkpoint**: User Stories 1 AND 2 both work — a Vendor's fulfillment action is visible to the
Customer end to end.

---

## Phase 5: User Story 3 - Administrator has fulfillment oversight (Priority: P3)

**Goal**: An Administrator can view fulfillment status and full history across every shop's order
lines from one read-only view.

**Independent Test**: As an Administrator, open `GET /api/admin/order-items` and confirm line
items from multiple vendors' shops are visible with status and history, and that no endpoint under
that path accepts a mutation.

### Tests for User Story 3 ⚠️

- [X] T020 [P] [US3] Contract test `GET /api/admin/order-items` — lists line items across every
      shop/vendor, paginated, each including shop/vendor identity and a `status_history` array
      ordered oldest-first (FR-007, FR-009) in `backend/tests/orders/test_admin_order_item_list.py`
- [X] T021 [P] [US3] Contract test: `PATCH`/`POST`/`DELETE` on `/api/admin/order-items` (and its
      detail path) are all rejected — oversight is read-only (FR-008, Acceptance Scenario 2) in
      `backend/tests/orders/test_admin_order_item_readonly.py`
- [X] T022 [P] [US3] Contract test: `status_history` is present only in the Administrator's
      response — the Vendor list/update response (US1) and the Customer order-detail response
      (US2) for the same line never include it (Clarifications session 2026-09-21) in
      `backend/tests/orders/test_order_item_history_visibility.py`

### Implementation for User Story 3

- [X] T023 [US3] Implement `OrderItemStatusEventSerializer` (`status`, `changed_at`) and
      `AdminOrderItemSerializer` (adds shop `{id, name}` and `status_history` — the nested
      `OrderItemStatusEventSerializer` list, ordered by `changed_at` ascending — to the same base
      fields as `VendorOrderItemSerializer`) in `backend/apps/orders/serializers.py` (depends on
      T001, T002, T011)
- [X] T024 [US3] Implement `AdminOrderItemListView` in `backend/apps/orders/views.py`:
      `IsAdministrator`; queryset `OrderItem.objects.select_related("product__shop", "order")
      .prefetch_related("status_events")` across all shops, paginated (Constitution Resource
      Utilization) (depends on T023)
- [X] T025 [US3] Wire `admin_urlpatterns` (`admin/order-items`) in `backend/apps/orders/urls.py`;
      include at `api/admin/` in `backend/config/urls.py` alongside the existing
      `apps.vendors.urls` admin include (depends on T024)
- [X] T026 [P] [US3] Add `listAdminOrderItems(page)` call to `frontend/src/lib/api-client.ts`
      (depends on T025)
- [X] T027 [P] [US3] Build `frontend/src/app/admin/orders/page.tsx`: read-only list across shops
      showing current status, shop/vendor name, and each line's expandable status history (depends
      on T026)

**Checkpoint**: All three user stories independently functional — Vendor fulfillment, Customer
visibility, and Administrator oversight all work end to end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T028 [P] Confirm `VendorOrderItemListView`'s and `AdminOrderItemListView`'s (T012, T024)
      pagination page size matches the existing `PAGE_SIZE = 20` DRF default (`config/settings.py`)
      that `OrderListView` already inherits (Constitution "Resource Utilization" — consistent list
      pagination across the app) in `backend/apps/orders/views.py`
- [ ] T029 Run all 5 `quickstart.md` scenarios end to end against real PostgreSQL with migrations
      applied, per Constitution Principle V
- [ ] T030 [P] Security/validation review pass: confirm every Vendor/Administrator `OrderItem`
      queryset filters by `request.user`'s own shop ownership or `IsAdministrator` at the
      queryset level, not only in serializers; confirm `VendorOrderItemStatusUpdateView` never
      trusts a client-supplied shop/vendor identifier, only the authenticated `request.user`
      resolved through `product__shop__owner` (Constitution Principle I) across
      `backend/apps/orders/`
- [ ] T031 [P] Extend `backend/README.md` with vendor-fulfillment setup notes: the widened
      `OrderItem.Status` choices, the new `OrderItemStatusEvent` history table, and the new
      `/api/vendor/order-items` / `/api/admin/order-items` endpoints

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks — nothing applies (see note above)
- **Foundational (Phase 2)**: BLOCKS all user stories — `OrderItem.Status`,
  `OrderItemStatusEvent`, and `advance_order_item_status()` are read or called by every later phase
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories
  - US2 (P1) depends on Foundational only (T001) for its regression test to have anything new to
    assert; does not depend on US1 being complete, though exercising it live is easiest once a
    Vendor can actually advance a line
  - US3 (P3) depends on Foundational (T002, the history table US1's service already writes to);
    does not depend on US1's endpoints existing, only on the data US1's service produces once
    exercised
  - In practice: implement in priority/dependency order **US1 → US2 → US3** — each is still an
    independently testable increment per its own Independent Test above
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and failing before implementation
- Models/migration (Foundational) before serializers
- Serializers before views
- Views before URL wiring
- Backend endpoint before its corresponding frontend page

### Parallel Opportunities

- Foundational: T002 (`OrderItemStatusEvent` model) and T005 (permissions) are independent files,
  both depend only on T001, and can run in parallel
- All contract tests within a story (marked [P]) can run in parallel with each other
- US3's tests (T020–T022) can run in parallel with each other; T026/T027 (frontend) can be staffed
  in parallel with T028–T031 (Polish) once US3's backend (T023–T025) lands
- US1 and US3's backend work can be staffed in parallel by different team members once Foundational
  is done, since US3 only reads what US1's service (Foundational T004) writes — it does not depend
  on US1's *endpoints*

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test GET /api/vendor/order-items in backend/tests/orders/test_vendor_order_item_list.py"
Task: "Contract test valid status transitions in backend/tests/orders/test_vendor_order_item_status_transitions.py"
Task: "Contract test invalid transition rejection in backend/tests/orders/test_vendor_order_item_invalid_transitions.py"
Task: "Contract test cross-vendor isolation in backend/tests/orders/test_vendor_order_item_isolation.py"
Task: "Contract test stock restoration + concurrency in backend/tests/orders/test_vendor_order_item_cancel_stock.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
2. Complete Phase 3: User Story 1
3. **STOP and VALIDATE**: run quickstart.md Scenario 1 independently
4. Demo: a Vendor can see and fulfill their own order lines

### Incremental Delivery

1. Foundational → widened status model, history table, transition service ready
2. US1 → validate (quickstart Scenario 1) → demo (Vendor fulfillment MVP)
3. US2 → validate (quickstart Scenario 2) → demo (Customer sees the Vendor's progress)
4. US3 → validate (quickstart Scenario 5) → demo (Administrator oversight)
5. Phase 6 polish (also exercises quickstart Scenarios 3–4's edge cases) → final review against
   Constitution before considering the feature done

### Constitution alignment (Principle V: Spec-Driven, Staged Delivery)

Per the Constitution, implementation MUST proceed in reviewable chunks — **one phase at a time**,
each run for real (migrations applied, endpoints exercised via the DRF browsable API or the actual
Next.js dev server) and reviewed before starting the next. Do not run `/speckit-implement` to
generate all 31 tasks unattended; implement and check off one phase (ideally one user story) at a
time.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability back to spec.md
- Each user story is independently completable and testable per its Independent Test statement
- Verify contract tests fail before implementing the view/serializer that makes them pass
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
- Total: 31 tasks (T001–T031) across Setup (0), Foundational (5), US1 (11), US2 (3), US3 (8),
  Polish (4)

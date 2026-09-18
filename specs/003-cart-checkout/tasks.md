---

description: "Task list template for feature implementation"
---

# Tasks: Shopping Cart & Checkout

**Input**: Design documents from `/specs/003-cart-checkout/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/cart-checkout-api.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context commits this feature to `pytest` +
`pytest-django` + `factory_boy` + DRF `APIClient`, calling out checkout atomicity/rollback
(FR-014, FR-016), order-history ownership isolation (FR-021), and live-data correctness (User
Story 3) as the highest-value test targets — checkout is the one place in this codebase so far
where a single request must all-or-nothing mutate three tables (Order, OrderItem, Product stock)
under a payment call and a row lock, so contract tests are written per behavior, first, before the
implementation that makes them pass.

**Organization**: Tasks are grouped by user story (P1–P3 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Paths follow `plan.md`'s Project Structure: `backend/apps/{cart,orders,payments}/`,
  `backend/tests/{cart,orders}/`, `frontend/src/app/{cart,checkout,orders,products}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the three new apps this feature lives in

- [X] T001 Create `cart`, `orders`, `payments` Django app skeletons (`__init__.py`,
      `migrations/__init__.py`) at `backend/apps/cart/`, `backend/apps/orders/`,
      `backend/apps/payments/`; register `"apps.cart"`, `"apps.orders"`, `"apps.payments"` in
      `INSTALLED_APPS` in `backend/config/settings.py` — no `apps.py`, matching the existing
      `apps.accounts`/`apps.vendors`/`apps.catalog` convention (no custom `AppConfig` anywhere in
      this codebase)

**Checkpoint**: Three apps registered, boot with no models/routes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Cart`/`CartItem` schema and shared live-pricing/availability logic every later
phase reads or extends

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — checkout (US2) reads
the same `Cart`/`CartItem` rows US1 writes, and US3's live-data correctness depends on the
availability computation living in one shared place from the start, not being bolted on later

- [X] T002 Create `Cart` model in `backend/apps/cart/models.py` per data-model.md:
      `customer` (`OneToOneField(User, related_name="cart", on_delete=CASCADE)`), `created_at`
      (`auto_now_add=True`), `updated_at` (`auto_now=True`)
- [X] T003 Create `CartItem` model in `backend/apps/cart/models.py` per data-model.md: `cart`
      (`ForeignKey(Cart, related_name="items", on_delete=CASCADE)`), `product`
      (`ForeignKey("catalog.Product", related_name="cart_items", on_delete=CASCADE)`), `quantity`
      (`PositiveIntegerField`, must be `>= 1` — FR-001), `created_at` (`auto_now_add=True`),
      `updated_at` (`auto_now=True`); add `UniqueConstraint(fields=["cart", "product"])` (FR-005,
      research.md §3) (depends on T002)
- [X] T004 Generate and apply the `cart` migration
      (`python manage.py makemigrations cart && python manage.py migrate`) (depends on T002, T003)
- [X] T005 [P] Add `CartFactory` and `CartItemFactory` to `backend/tests/factories.py`, mirroring
      the existing `ProductFactory` pattern (depends on T004)
- [X] T006 [P] Implement live-pricing/availability computation on `CartItem` in
      `backend/apps/cart/models.py` — properties `unit_price` (= `product.price`), `subtotal` (=
      `product.price * quantity`), `unavailable_reason` (returns the first applicable reason —
      unpublished/soft-deleted, shop not APPROVED, or quantity exceeding stock — or `None`), and
      `is_available` (= `unavailable_reason is None`) per data-model.md's CartItem "Computed, not
      stored" rules — plain model properties, not serializer method fields, so both the cart view
      (US1) and `place_order()`'s re-validation (US2) call the exact same logic without cross-app
      serializer imports (depends on T004)

**Checkpoint**: `Cart`/`CartItem` schema and shared availability logic exist. User story
implementation can now begin.

---

## Phase 3: User Story 1 - Customer builds and manages a persistent cart (Priority: P1) 🎯 MVP

**Goal**: A logged-in Customer can add published products to a cart with a quantity, see it
persist across logins/devices, adjust quantities, and remove lines.

**Independent Test**: Log in as a Customer, add two different published products to the cart with
different quantities, log out and back in (or hit the API fresh) and confirm the same cart
contents are returned, then adjust a quantity and remove a line and confirm the cart reflects both
changes.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T007 [P] [US1] Contract test `GET /api/cart` — creates the cart lazily on first access
      (research.md §1) and returns the empty-cart shape `{"items": [], "total": "0.00"}` for a
      fresh Customer (FR-002, Edge Cases) in `backend/tests/cart/test_cart_view.py` (2 tests, also
      covers the `IsCustomer` role gate)
- [X] T008 [P] [US1] Contract test `POST /api/cart/items` — `201` with a correct subtotal
      (unit price × quantity) for `quantity >= 1` (FR-001); `400` for `quantity < 1`; `400` with a
      message stating the maximum available quantity when the requested quantity exceeds
      `product.stock_quantity` (FR-007); `400` for an unpublished product in
      `backend/tests/cart/test_cart_item_create.py` (4 tests)
- [X] T009 [P] [US1] Contract test: `POST /api/cart/items` twice with the same `product_id` —
      second call returns `200` and merges into the existing line's `quantity` rather than
      creating a second line (FR-005) in `backend/tests/cart/test_cart_item_merge.py` (2 tests)
- [X] T010 [P] [US1] Contract test `PATCH /api/cart/items/{id}` — updates `quantity` and
      recalculates subtotal/total (FR-003); `400` when the new quantity exceeds current stock
      (FR-007); `404` when the line belongs to a different Customer (FR-018) in
      `backend/tests/cart/test_cart_item_update.py` (3 tests)
- [X] T011 [P] [US1] Contract test `DELETE /api/cart/items/{id}` — `204`, removes exactly one
      line, the remaining line(s) and recomputed total are unaffected (FR-004); `404` when the
      line belongs to a different Customer (FR-018) in
      `backend/tests/cart/test_cart_item_delete.py` (2 tests)
- [X] T012 [P] [US1] Contract test: a Customer's cart contents are identical across two separate
      authenticated requests (simulating logout/login or a different device) — same items and
      quantities both times (FR-006) in `backend/tests/cart/test_cart_persistence.py` (1 test).
      **14 tests total for T007–T012, all passing.**

### Implementation for User Story 1

- [X] T013 [US1] Implemented `CartSerializer`/`CartItemSerializer` (read) in
      `backend/apps/cart/serializers.py`: `unit_price`/`subtotal` declared as plain
      `DecimalField(read_only=True)` (DRF resolves them from T006's same-named properties via
      `getattr`), `is_available`/`unavailable_reason` likewise; `Cart.total` sums only
      `is_available` lines and returns a quantized string (`"0.00"`) rather than a raw `Decimal`,
      matching how `DecimalField` already string-coerces elsewhere in this codebase — a
      `SerializerMethodField` does not get that coercion for free (depends on T006)
- [X] T014 [US1] Implemented `CartItemCreateSerializer` in `backend/apps/cart/serializers.py`:
      `product_id` is a `PrimaryKeyRelatedField` scoped to `Product.objects.filter(is_published=
      True)` (soft-deleted rows already excluded by the catalog app's own default manager), so an
      unpublished/nonexistent/soft-deleted product 400s automatically; `validate_product_id`
      additionally checks `shop.status == APPROVED`; `validate()` checks the single request's
      `quantity` against current stock (FR-007) — the *combined* quantity check for an
      already-present line (FR-005) is left to the view (T016), since a bare serializer has no way
      to see the existing line. **Deviation from the original single-serializer sketch**: split
      into `CartItemCreateSerializer` (POST) and `CartItemUpdateSerializer` (PATCH, validates
      against `self.instance.product.stock_quantity`) — the two have different validation shapes
      (one has no instance yet) (depends on T003)
- [X] T015 [US1] Implemented `CartDetailView` in `backend/apps/cart/views.py`: `Cart.objects.
      get_or_create(customer=request.user)` (research.md §1) then re-fetches with
      `prefetch_related("items__product__shop")` for the actual response to avoid N+1 queries
      across lines; `IsCustomer` (depends on T013)
- [X] T016 [US1] Implemented `CartItemCreateView` in `backend/apps/cart/views.py`: `CartItem.
      objects.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})`; when an
      existing line is found, increments and re-validates the combined quantity against
      `product.stock_quantity`, raising `ValidationError` (400) if it's now over (FR-005,
      research.md §3); returns `201` for a new line, `200` for a merge (depends on T014)
- [X] T017 [US1] Implemented `CartItemDetailView` (`PATCH`/`DELETE`) in
      `backend/apps/cart/views.py`: `get_object_or_404(CartItem, pk=item_id, cart__customer=
      request.user)` so another Customer's line ID 404s (FR-018, research.md §6); `IsCustomer`
      (depends on T014)
- [X] T018 [US1] Wired `backend/apps/cart/urls.py` and included it at `path("api/", include(...))`
      in `backend/config/urls.py`. **Deviation from contracts/cart-checkout-api.md's illustrative
      trailing-slash examples**: used `cart`, `cart/items`, `cart/items/<int:item_id>` with no
      trailing slash, matching the no-trailing-slash convention already established by
      `apps.catalog.urls`/`apps.vendors.urls` throughout this codebase (depends on T015, T016,
      T017)
- [X] T019 [US1] **Deviation**: `frontend/src/lib/api-client.ts` has no domain-specific wrapper
      functions for any existing feature (catalog, vendors, accounts all call the generic
      `apiFetch<T>()` directly from each page) — added none here either, to stay consistent; cart
      calls are inlined in T020/T021 instead (depends on T018)
- [X] T020 [P] [US1] Built `frontend/src/app/cart/page.tsx`: lists cart lines with a quantity
      input (`PATCH` on change) and a remove button (`DELETE`), shows the total, flags any
      `is_available: false` line with its `unavailable_reason` (pulled forward from US3's T045
      since the data was already in T013's response shape — T045's remaining scope is just
      disabling the checkout button) (depends on T019)
- [X] T021 [P] [US1] Added an "Add to Cart" control (quantity input + submit) to
      `frontend/src/app/products/[id]/page.tsx`, gated on `useAuth()`'s `user.role === "CUSTOMER"`
      with a log-in prompt for anonymous visitors and a role message for Vendor/Administrator
      accounts (depends on T019)

**Bug fixed while running this end-to-end** (Constitution Principle V): the initial cart-loading
`useEffect` called a `useCallback`-wrapped `loadCart()` directly in the effect body, which trips
the `react-hooks/set-state-in-effect` lint rule (cascading-render risk) even though it's the exact
async-fetch-on-mount pattern used elsewhere in this codebase. Rewrote it as an inline async
function with a `cancelled` flag, matching `vendor/products/page.tsx`'s and
`products/[id]/page.tsx`'s existing pattern; `loadCart()` remains as a `useCallback` for the
mutation handlers (quantity change, remove) to call after their own action succeeds.

**Manually verified live** (real Postgres + `runserver` + `next dev`): full curl walkthrough of
quickstart.md Scenario 1 (add, merge-on-duplicate-add with combined-quantity stock check, quantity
update, remove, over-stock rejection with the "Only N available." message, persistence across a
fresh login, and a 404 on another Customer's cart-item ID) — all passing exactly as specified.
Also walked through it in the browser via `claude-in-chrome`: logged in, added a product from its
detail page ("Added to cart."), viewed `/cart` showing both lines and the correct total, removed
one line and confirmed the total recalculated. (The browser session hit repeated Chrome
autofill/autocomplete interference on the *login form* specifically — pre-existing
`login/page.tsx` from 001-accounts-auth, not touched by this feature — that turned out to be a
testing-environment artifact, not an app bug: a raw `fetch()` to `/api/auth/login` from the same
page context succeeded immediately with correct credentials.) Full backend suite re-run clean: 112
passed (98 existing + 14 new).

**Checkpoint**: User Story 1 is fully functional and independently testable — a Customer can
build and manage a persistent cart end to end, backend and frontend.

---

## Phase 4: User Story 2 - Customer completes checkout and places an order (Priority: P1)

**Goal**: A Customer with items in their cart can submit shipping details, have every line
re-validated and paid (mocked) atomically, and receive a placed `Order`; their cart is emptied and
stock is decremented exactly once per line.

**Independent Test**: Log in as a Customer with a non-empty cart, submit shipping details and
confirm checkout, and verify an `Order` is created with the correct line items/prices/shipping
details and a per-line-item status for each vendor's products, that the ordered products' stock
was decremented by the ordered amounts, and that the cart is now empty.

### Tests for User Story 2 ⚠️

- [ ] T022 [P] [US2] Contract test `POST /api/checkout/` happy path, single-vendor cart — `201`,
      an `Order` with one `OrderItem` per cart line (correct product/quantity/`unit_price`
      captured), cart emptied, each ordered product's `stock_quantity` decremented by the ordered
      amount (FR-012, FR-014, FR-017) in `backend/tests/orders/test_checkout_success.py`
- [ ] T023 [P] [US2] Contract test `POST /api/checkout/` with a cart spanning two vendors' shops —
      `201`, a single `Order` whose `items` include lines from both shops, each carrying its own
      `status` independently (FR-013) in `backend/tests/orders/test_checkout_multi_vendor.py`
- [ ] T024 [P] [US2] Contract test `POST /api/checkout/` with an empty cart — `400`, no `Order`
      created (FR-011) in `backend/tests/orders/test_checkout_empty_cart.py`
- [ ] T025 [P] [US2] Contract test `POST /api/checkout/` where a cart line's quantity now exceeds
      current stock (stock reduced after the item was added) — `400` naming the specific line, no
      `Order` created, no stock decremented (FR-008, Edge Cases) in
      `backend/tests/orders/test_checkout_stale_stock.py`
- [ ] T026 [P] [US2] Contract test `POST /api/checkout/` with `payment_method: "declined"`
      (research.md §5 sentinel) — `400`, no `Order` created, no stock decremented, cart unchanged
      afterward (FR-016) in `backend/tests/orders/test_checkout_payment_failure.py`
- [ ] T027 [P] [US2] Contract test `POST /api/checkout/` with a missing/invalid shipping field —
      `400` with a field-level error naming the failed field, no `Order` created (FR-009, FR-010)
      in `backend/tests/orders/test_checkout_shipping_validation.py`
- [ ] T028 [P] [US2] Concurrency test: two different Customers' carts each hold `quantity: 1` of a
      product with `stock_quantity: 1`; fire both checkouts concurrently (separate threads/DB
      connections) — exactly one `201`, the other a `400` stock-conflict, final `stock_quantity`
      is `0`, never negative, and no partial `Order` is left behind (Edge Cases, research.md §4)
      in `backend/tests/orders/test_checkout_concurrency.py`

### Implementation for User Story 2

- [ ] T029 [US2] Create `Order` model in `backend/apps/orders/models.py` per data-model.md:
      `customer` (`ForeignKey(User, related_name="orders", on_delete=CASCADE)`), `status`
      (`CharField`, `choices=Order.Status`, only `PLACED` reachable in this feature), shipping
      fields `recipient_name`, `address_line`, `city`, `region`, `postal_code`, `country`, `phone`
      (all required `CharField`, FR-009), `placed_at` (`auto_now_add=True`)
- [ ] T030 [US2] Create `OrderItem` model in `backend/apps/orders/models.py` per data-model.md:
      `order` (`ForeignKey(Order, related_name="items", on_delete=CASCADE)`), `product`
      (`ForeignKey("catalog.Product", related_name="order_items", on_delete=PROTECT)` — `PROTECT`,
      never `CASCADE`, so a referenced product row can never be removed out from under a
      historical order line), `quantity` (`PositiveIntegerField`), `unit_price`
      (`DecimalField(max_digits=10, decimal_places=2)`, frozen at order-creation time), `status`
      (`CharField`, `choices=OrderItem.Status`, only `PENDING` reachable in this feature —
      Constitution Principle VI, FR-013) (depends on T029)
- [ ] T031 [P] [US2] Create `PaymentRecord` model in `backend/apps/payments/models.py` per
      data-model.md: `order` (`OneToOneField("orders.Order", related_name="payment", on_delete=
      CASCADE)`), `method` (`CharField(max_length=50)` — a label only, never raw card data,
      Constitution Principle III), `status` (`CharField`, `choices=PaymentRecord.Status`, only
      `SUCCEEDED` reachable — a failed attempt never reaches row creation, research.md §5),
      `transaction_reference` (`CharField(max_length=64, unique=True)`, a generated opaque
      reference), `created_at` (`auto_now_add=True`) (depends on T029)
- [ ] T032 Generate and apply the `orders` and `payments` migrations
      (`python manage.py makemigrations orders payments && python manage.py migrate`) (depends on
      T030, T031)
- [ ] T033 [US2] Implement `PaymentService` (ABC, one `charge(*, amount, method) -> PaymentResult`
      method) and `MockPaymentService` in `backend/apps/payments/services.py`, plus a
      `get_payment_service()` factory, mirroring `apps/core/email.py`'s `EmailService` /
      `DjangoEmailService` / `get_email_service()` pattern exactly; `charge()` accepts only an
      opaque `method` label, never card fields; the case-insensitive sentinel method value
      `"declined"` deterministically fails, everything else succeeds (research.md §5) (depends on
      T031)
- [ ] T034 [US2] Implement `place_order(customer, shipping_data, payment_method)` in
      `backend/apps/orders/services.py`: one `transaction.atomic()` block; `select_for_update()`
      on the touched `Product` rows, always acquired in ascending `product_id` order to avoid
      deadlocks (research.md §4); re-validate every cart line via T006's `is_available`/current
      stock; raise a checkout error naming the failing line(s) if any line fails, or if no
      available lines remain (FR-008, FR-011); call `get_payment_service().charge()`; only on
      success, create the `Order` + one `OrderItem` per line (capturing `unit_price` from the
      live `product.price`, FR-012) + `PaymentRecord`, decrement each `Product.stock_quantity` by
      the ordered amount (FR-014), and delete the Customer's `CartItem` rows (FR-017) (depends on
      T006, T029, T030, T031, T033)
- [ ] T035 [US2] Implement `CheckoutSerializer` (nested shipping fields + `payment_method`) and
      `OrderSerializer`/`OrderDetailSerializer` in `backend/apps/orders/serializers.py` matching
      contracts/cart-checkout-api.md's request/response shapes (depends on T029, T030)
- [ ] T036 [US2] Implement `CheckoutView` in `backend/apps/orders/views.py`: `IsCustomer`,
      validates the request with T035's `CheckoutSerializer`, calls T034's `place_order()`, and
      translates its error cases to the `400` response shapes in contracts/cart-checkout-api.md
      (empty cart, stale lines, payment declined, shipping validation) (depends on T034, T035)
- [ ] T037 [US2] Wire a `checkout_urlpatterns` list (`checkout/`) in
      `backend/apps/orders/urls.py`, included directly at `/api/` in `backend/config/urls.py`
      alongside T018's cart include (research.md §8) (depends on T036)
- [ ] T038 [US2] Add a `checkout(shippingData, paymentMethod)` call to
      `frontend/src/lib/api-client.ts` (depends on T037)
- [ ] T039 [US2] Build `frontend/src/app/checkout/page.tsx`: shipping form + payment method
      selector + confirm action, redirecting to the order confirmation on success (T053) and
      showing the specific error (empty cart / stale line / payment declined / field validation)
      on failure (depends on T038)

**Checkpoint**: User Stories 1 AND 2 both work — the full cart→checkout→order lifecycle is
functional end to end, backend and frontend.

---

## Phase 5: User Story 3 - Cart reflects live catalog changes (Priority: P2)

**Goal**: A Customer's cart and checkout always reflect the *current* price, availability, and
publish/approval status of each product, never stale data from when it was added.

**Independent Test**: Add a product to a cart, have a vendor change its price/stock/publish status
directly via the catalog feature, then view the cart and attempt checkout — confirm the cart
displays current data and checkout enforces it.

> T006 and T013 already made price live-read-only (no `unit_price` column ever existed on
> `CartItem`, research.md §2) and T034 already re-validates every line at checkout. This phase's
> job is to lock the remaining availability-flagging behavior in with dedicated tests, close any
> gap they expose, and add the UI treatment that wasn't needed for US1/US2's minimal flows.

### Tests for User Story 3 ⚠️

- [ ] T040 [P] [US3] Contract test: change a cart product's `price` via the catalog API after it
      was added to the cart — `GET /api/cart/` reflects the new price and a recalculated subtotal,
      never the add-time price (Scenario 1) in `backend/tests/cart/test_cart_live_price.py`
- [ ] T041 [P] [US3] Contract test: unpublish a cart product — `GET /api/cart/` flags that line
      `is_available: false` with an `unavailable_reason`, and `total` excludes its subtotal
      (Scenario 2) in `backend/tests/cart/test_cart_unavailable_unpublished.py`
- [ ] T042 [P] [US3] Contract test: change a cart product's owning shop to PENDING or REJECTED —
      the line shows the same `is_available: false` behavior as an unpublished product (Edge
      Cases) in `backend/tests/cart/test_cart_unavailable_shop_unapproved.py`
- [ ] T043 [P] [US3] Contract test `POST /api/checkout/` with an unavailable line still present —
      `400`, checkout blocked until the Customer removes or adjusts that line, same response shape
      as T025 (Scenario 3) in `backend/tests/orders/test_checkout_unavailable_line.py`

### Implementation for User Story 3

- [ ] T044 [US3] Fix any gap T040–T042 expose in `CartItem.is_available`/`unavailable_reason`
      (T006) so all three staleness cases (price — already live by construction; unpublished; shop
      no longer APPROVED) are correctly flagged in `backend/apps/cart/models.py` (depends on T006,
      T040, T041, T042)
- [ ] T045 [P] [US3] Update `frontend/src/app/cart/page.tsx` to visually flag unavailable lines
      (badge + reason text) and disable the checkout button while any unavailable line remains
      (depends on T020, T044)

**Checkpoint**: All three P1/P2 stories are independently functional — the cart's correctness/
trust safeguard is proven end to end.

---

## Phase 6: User Story 4 - Customer reviews past orders (Priority: P3)

**Goal**: A Customer can list their own past orders and open any one to review its full detail.

**Independent Test**: Place two separate orders as the same Customer, request the Customer's order
list and confirm both appear with correct summaries, and open one to confirm its full detail
matches what was ordered.

### Tests for User Story 4 ⚠️

- [ ] T046 [P] [US4] Contract test `GET /api/orders/` — lists only the requester's own orders,
      paginated, most recent first (FR-020) in `backend/tests/orders/test_order_list.py`
- [ ] T047 [P] [US4] Contract test `GET /api/orders/{id}/` — full detail: every line item
      (product, quantity, price paid), shipping details, and each line's current `status` (FR-019,
      FR-020) in `backend/tests/orders/test_order_detail.py`
- [ ] T048 [P] [US4] Contract test `GET /api/orders/{id}/` using another Customer's order ID —
      `404`, not that order's data, in both cases indistinguishable from a nonexistent ID (FR-021,
      research.md §6) in `backend/tests/orders/test_order_detail_isolation.py`

### Implementation for User Story 4

- [ ] T049 [US4] Implement `OrderListView` in `backend/apps/orders/views.py`: queryset
      `Order.objects.filter(customer=request.user).order_by("-placed_at")`, paginated,
      `IsCustomer` (depends on T035)
- [ ] T050 [US4] Implement `OrderDetailView` in `backend/apps/orders/views.py`: queryset filtered
      to `customer=request.user` at the queryset level so another Customer's order ID 404s
      (research.md §6), `IsCustomer` (depends on T035)
- [ ] T051 [US4] Wire the default `urlpatterns` (`orders/`, `orders/<int:order_id>/`) in
      `backend/apps/orders/urls.py` and include under `/api/orders/` in
      `backend/config/urls.py` (depends on T049, T050)
- [ ] T052 [US4] Add `listOrders`/`getOrder` calls to `frontend/src/lib/api-client.ts` (depends on
      T051)
- [ ] T053 [P] [US4] Build `frontend/src/app/orders/page.tsx` (order history list) and
      `frontend/src/app/orders/[id]/page.tsx` (order detail — also the page T039's checkout
      confirmation redirects to) (depends on T052)

**Checkpoint**: All four user stories independently functional — the full Shopping Cart &
Checkout feature works end to end.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T054 [P] Confirm `OrderListView`'s (T049) pagination page size is sane per Constitution
      "Resource Utilization" in `backend/apps/orders/views.py`
- [ ] T055 Run all 5 `quickstart.md` scenarios end to end against real PostgreSQL with migrations
      applied, including the concurrency scenario (Scenario 5), per Constitution Principle V
- [ ] T056 [P] Security/validation review pass: confirm `PaymentService.charge()` (T033) never
      accepts or could persist raw card data; confirm `customer`/`product`/`shop` cannot be
      spoofed via a crafted checkout or cart-item body; confirm every `Cart`/`CartItem`/`Order`
      queryset filters by `request.user` at the queryset level, not only in serializers
      (Constitution Principle I/III) across `backend/apps/cart/`, `backend/apps/orders/`,
      `backend/apps/payments/`
- [ ] T057 [P] Extend `backend/README.md` with cart/checkout setup notes: the three new apps, that
      no new dependencies were added, and the mock payment `"declined"` sentinel used for testing
      (research.md §5)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (`Cart`/
  `CartItem` schema and the shared availability computation are read or extended by every later
  phase)
- **User Stories (Phase 3–6)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories
  - US2 (P1) depends on US1's `Cart`/`CartItem` rows existing to check out from — build after US1
  - US3 (P2) depends on US1 (cart display) and US2 (checkout re-validation) already existing to
    extend/harden — build after both
  - US4 (P3) depends on US2's `Order`/`OrderItem` models existing — build after US2
  - In practice: implement in priority/dependency order **US1 → US2 → US3 → US4** — each is still
    an independently testable increment per its own Independent Test above
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and failing before implementation
- Models (Foundational) before serializers
- Serializers before views
- Views before URL wiring
- Backend endpoint before its corresponding frontend page
- Story's backend fully working before its frontend is wired to it

### Parallel Opportunities

- Foundational: T005 (factories) and T006 (availability logic) are independent files, both depend
  only on T004, and can run in parallel
- All contract tests within a story (marked [P]) can run in parallel with each other
- US1's two frontend tasks (T020, T021) can run in parallel once T019 lands
- US2's model tasks: T031 (`payments/models.py`) can run in parallel with T030 once T029 lands
  (different files)
- US3's backend hardening (T044) and frontend flagging (T045) both depend on Foundational + US1's
  cart page, and can be staffed in parallel with US4 once US2 is done, since neither touches
  `orders/` files
- Different user stories can be worked on in parallel by different team members once their
  respective dependencies (above) are satisfied

---

## Parallel Example: User Story 2

```bash
# Launch all contract tests for User Story 2 together:
Task: "Contract test POST /api/checkout/ happy path in backend/tests/orders/test_checkout_success.py"
Task: "Contract test POST /api/checkout/ multi-vendor cart in backend/tests/orders/test_checkout_multi_vendor.py"
Task: "Contract test POST /api/checkout/ empty cart in backend/tests/orders/test_checkout_empty_cart.py"
Task: "Contract test POST /api/checkout/ stale stock in backend/tests/orders/test_checkout_stale_stock.py"
Task: "Contract test POST /api/checkout/ payment declined in backend/tests/orders/test_checkout_payment_failure.py"
Task: "Contract test POST /api/checkout/ shipping validation in backend/tests/orders/test_checkout_shipping_validation.py"
Task: "Concurrency test for checkout oversell race in backend/tests/orders/test_checkout_concurrency.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 independently
5. Demo: Customer can add, view, adjust, and remove cart items, persisted server-side

### Incremental Delivery

1. Setup + Foundational → `Cart`/`CartItem` schema and shared availability logic ready
2. US1 → validate (quickstart Scenario 1) → demo (persistent cart MVP)
3. US2 → validate (Scenario 2) → demo (full cart→checkout→order lifecycle)
4. US3 → validate (Scenario 3) → demo (cart/checkout correctness under live catalog changes)
5. US4 → validate (Scenario 4) → demo (order history)
6. Phase 7 polish (also exercises Scenario 5's concurrency check) → final review against
   Constitution before considering the feature done

### Constitution alignment (Principle V: Spec-Driven, Staged Delivery)

Per the Constitution, implementation MUST proceed in reviewable chunks — **one phase at a time**,
each run for real (migrations applied, endpoints exercised via the DRF browsable API or the actual
Next.js dev server) and reviewed before starting the next. Do not run `/speckit-implement` to
generate all 57 tasks unattended; implement and check off one phase (ideally one user story) at a
time.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability back to spec.md
- Each user story is independently completable and testable per its Independent Test statement
- Verify contract tests fail before implementing the view/serializer that makes them pass
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
- Total: 57 tasks (T001–T057) across Setup (1), Foundational (5), US1 (15), US2 (18), US3 (6),
  US4 (8), Polish (4)

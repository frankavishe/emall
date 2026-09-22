---

description: "Task list template for feature implementation"
---

# Tasks: Role-Aware Homepage & Shared Navigation

**Input**: Design documents from `/specs/006-homepage-navigation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/homepage-api.md, quickstart.md

**Tests**: Included for the one backend change (shared pagination class), per plan.md's Technical
Context. No frontend automated test suite exists in this repo (001-005 precedent); frontend work
is verified via the manual `quickstart.md` scenarios instead.

**Organization**: Tasks are grouped by user story (US1-US5 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Paths follow plan.md's Project Structure: no new Django app; `backend/apps/core/pagination.py`
  is new, `backend/apps/{catalog,orders,vendors}/views.py` are extended in place;
  `frontend/src/app/page.tsx` is rewritten, `frontend/src/components/nav.tsx` is new,
  `frontend/src/app/layout.tsx`/`login/page.tsx`/`register/page.tsx` are extended in place

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the test package the Foundational phase's pagination test needs

- [X] T001 [P] Create `backend/tests/core/__init__.py` (new test package) if it does not already
      exist, so `backend/tests/core/test_pagination.py` (T003) has somewhere to live

**Checkpoint**: Test scaffolding ready.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared pagination class that User Stories 1, 4, and 5 all depend on to
request small, bounded result sets from existing endpoints

**⚠️ CRITICAL**: No user story's backend wiring (T004, T013, T017, T018) can begin until this
phase is complete

- [X] T002 Create `LimitedPageNumberPagination` in `backend/apps/core/pagination.py`: extends
      `rest_framework.pagination.PageNumberPagination`, sets `page_size_query_param = "page_size"`
      and `max_page_size = 24`; do not override `page_size` itself so the existing default of 20
      (from `backend/config/settings.py`'s `REST_FRAMEWORK["PAGE_SIZE"]`) is unchanged when the
      query param is omitted (contracts/homepage-api.md)
- [X] T003 [P] Add `backend/tests/core/test_pagination.py`: (a) a list view using
      `LimitedPageNumberPagination` returns 20 results by default when `page_size` is omitted,
      unchanged from today; (b) `?page_size=5` returns exactly 5 results; (c) `?page_size=100`
      (above `max_page_size=24`) is capped at 24 results, not rejected with an error (depends on
      T002)

**Checkpoint**: Pagination class exists and is tested. User story implementation can now begin.

---

## Phase 3: User Story 1 - Guest visitor lands on a welcoming homepage (Priority: P1) 🎯 MVP

**Goal**: A logged-out visitor opens `/` and sees a marketing/landing view with product highlights
and Login/Register CTAs instead of the current Next.js boilerplate.

**Independent Test**: Open `/` in a logged-out session; confirm product highlights and visible
Login/Register CTAs, no errors, no placeholder content (quickstart.md Scenario 1).

### Implementation for User Story 1

- [X] T004 [US1] Set `pagination_class = LimitedPageNumberPagination` on `CatalogProductListView`
      in `backend/apps/catalog/views.py` (depends on T002)
- [X] T005 [P] [US1] Add `listProducts(limit?: number)` to `frontend/src/lib/api-client.ts`:
      `GET /api/catalog/products` with an optional `?page_size=${limit}` query param, typed
      `Promise<PaginatedResponse<CatalogProduct>>` (reuse the `CatalogProduct`-shaped type already
      used inline in `frontend/src/app/products/page.tsx`) (depends on T004)
- [X] T006 [US1] Rewrite `frontend/src/app/page.tsx`'s guest branch (`useAuth()`'s `user === null`,
      gated on `isLoading`): a marketing/landing hero section, a product-highlights grid fetched
      via `listProducts(8)`, and visible Login/Register CTA links (FR-002); an explicit loading
      state while fetching, an explicit empty state when the catalog has zero products (edge
      case), and an explicit error/retry state on fetch failure (FR-011, FR-012) (depends on T005)
- [X] T007 [US1] Review the guest branch built in T006 and confirm it renders no vendor/admin-only
      data and no customer-only cart/orders links (FR-002 Acceptance Scenario 2); adjust if
      anything leaked (depends on T006)

**Checkpoint**: Guest homepage is fully functional and independently testable (quickstart.md
Scenario 1). This is the MVP.

---

## Phase 4: User Story 2 - Any visitor navigates the app via a shared, role-aware nav bar (Priority: P1)

**Goal**: A navigation bar appears on every page, with links that change based on the visitor's
role (guest / Customer / Vendor / Administrator).

**Independent Test**: As each of the four visitor types, load any page and confirm the nav bar is
present with links matching that type (quickstart.md Scenario 2).

### Implementation for User Story 2

- [X] T008 [US2] Create `frontend/src/components/nav.tsx`: a client component reading `useAuth()`'s
      `user`/`role`/`logout`, rendering the link set from research.md §5 —
      guest: Home, Products, Login, Register;
      Customer: Home, Products, Cart, Orders, Account, Logout;
      Vendor: Home, My Products, Vendor Orders, Account, Logout;
      Administrator: Home, Shop Approvals, Order Oversight, Account, Logout
      (FR-007, FR-008)
- [X] T009 [US2] Render `<Nav />` in `frontend/src/app/layout.tsx`, above `{children}` and inside
      the existing `<AuthProvider>`, so it appears on every route (depends on T008)
- [X] T010 [US2] Manually verify the nav updates correctly across auth-state transitions — guest →
      logged in as each role → logged out again reverts to guest links (FR-013) — by walking
      quickstart.md Scenarios 2 and 6 (depends on T009)

**Checkpoint**: Nav bar present and role-correct on every page (quickstart.md Scenario 2).

---

## Phase 5: User Story 3 - Customer sees a personalized shopping homepage (Priority: P2)

**Goal**: A logged-in Customer sees featured/recent products and links to their cart and orders,
instead of the guest marketing view.

**Independent Test**: Log in as a Customer, open `/`, confirm featured/recent products and
cart/orders links, no guest CTAs (quickstart.md Scenario 3).

### Implementation for User Story 3

- [X] T011 [US3] Extend `frontend/src/app/page.tsx` with a Customer branch
      (`user.role === "CUSTOMER"`): featured/recent products via `listProducts(8)` (T005), links to
      `/cart` and `/orders`; no guest CTAs, no Vendor/Administrator content (FR-003); loading/
      empty/error states per FR-011/FR-012 (depends on T006, T005)
- [X] T012 [US3] Manually confirm an empty cart and empty order history still render working
      links with no errors (FR-003 Acceptance Scenario 3), and that the Customer branch shows no
      guest CTAs and no Vendor/Administrator-only content (FR-003, SC-003), per quickstart.md
      Scenario 3 (depends on T011)

**Checkpoint**: Customer homepage functional (quickstart.md Scenario 3).

---

## Phase 6: User Story 4 - Vendor sees a business summary homepage (Priority: P2)

**Goal**: A logged-in Vendor sees their shop's approval status, recent orders for their shop, and
a link to manage products — correctly for all three shop states plus "no shop yet".

**Independent Test**: Log in as a Vendor in each shop state (none, PENDING, APPROVED, REJECTED)
and confirm the homepage matches (quickstart.md Scenario 4).

### Implementation for User Story 4

- [X] T013 [US4] Set `pagination_class = LimitedPageNumberPagination` on
      `VendorOrderItemListView` in `backend/apps/orders/views.py` (depends on T002)
- [X] T014 [P] [US4] Extend `listVendorOrderItems` in `frontend/src/lib/api-client.ts` with an
      optional `limit` parameter that appends `&page_size=${limit}` to the existing
      `GET /api/vendor/order-items?page=${page}` call; omitting `limit` MUST preserve today's
      behavior exactly (depends on T013)
- [X] T015 [US4] Extend `frontend/src/app/page.tsx` with a Vendor branch
      (`user.role === "VENDOR"`), reading shop status from already-loaded `user.shops` (no extra
      fetch, research.md §2):
      - no shop → prompt to request one, linking to `/account` (FR-005)
      - PENDING → show pending status; no order/product-management content presented as active
        (FR-004 Acceptance Scenario 2)
      - REJECTED → show rejected status and a link to `/account` (FR-005; spec Clarifications)
      - APPROVED → show approved status, recent orders via `listVendorOrderItems(1, 5)` (T014), a
        link to `/vendor/products` (FR-004); explicit empty state when there are zero orders
        (FR-011)
      (depends on T014)
- [X] T016 [US4] Manually confirm all four shop states render distinct, correct content, and that
      the Vendor branch shows no guest CTAs, no Customer cart/orders links, and no
      Administrator-only content (FR-004, FR-005, SC-003), per quickstart.md Scenario 4 (depends
      on T015)

**Checkpoint**: Vendor homepage functional across all shop states (quickstart.md Scenario 4).

---

## Phase 7: User Story 5 - Administrator sees an operational summary homepage (Priority: P3)

**Goal**: A logged-in Administrator sees the count of shops pending approval, recent orders across
the platform, and links into the shop-approvals and order-oversight pages.

**Independent Test**: Log in as an Administrator with pending shops and recent orders present;
confirm the count, order list, and links (quickstart.md Scenario 5).

### Implementation for User Story 5

- [ ] T017 [P] [US5] Set `pagination_class = LimitedPageNumberPagination` on `AdminShopListView`
      in `backend/apps/vendors/views.py` (depends on T002)
- [ ] T018 [P] [US5] Set `pagination_class = LimitedPageNumberPagination` on
      `AdminOrderItemListView` in `backend/apps/orders/views.py` (depends on T002)
- [ ] T019 [P] [US5] Add `listAdminShops(status?: string, limit?: number)` to
      `frontend/src/lib/api-client.ts`: `GET /api/admin/shops` with optional `?status=` and
      `?page_size=`, typed `Promise<PaginatedResponse<AdminShop>>` — this widens the currently
      under-typed inline call in `frontend/src/app/admin/shops/page.tsx` (data-model.md) (depends
      on T017)
- [ ] T020 [US5] Extend `listAdminOrderItems` in `frontend/src/lib/api-client.ts` with an
      optional `limit` parameter that appends `&page_size=${limit}`; omitting `limit` MUST
      preserve today's behavior exactly. Sequenced after T019 (not marked [P]) since both edit
      `api-client.ts` (depends on T018, T019)
- [ ] T021 [US5] Extend `frontend/src/app/page.tsx` with an Administrator branch
      (`user.role === "ADMINISTRATOR"`): pending-shop count via
      `listAdminShops("PENDING", 1)` reading the response's `.count` field (FR-006, research.md
      §3), recent platform orders via `listAdminOrderItems(1, 5)`, links to `/admin/shops` and
      `/admin/orders`; explicit zero-count state (FR-006 Acceptance Scenario 2), loading/error
      states (FR-011/FR-012) (depends on T019, T020)
- [ ] T022 [US5] Manually confirm the pending-shop count reflects the full filtered queryset (not
      just the returned page) and updates after shops are approved/rejected, and that the
      Administrator branch shows no guest CTAs and no Customer/Vendor-only content (FR-006,
      SC-003), per quickstart.md Scenario 5 (depends on T021)

**Checkpoint**: Admin homepage functional (quickstart.md Scenario 5). All five user stories now
independently work.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: The login/register redirect change (applies across all roles) and final verification

- [ ] T023 [P] In `frontend/src/app/login/page.tsx`, change the post-login
      `router.push("/account")` to `router.push("/")` (FR-014)
- [ ] T024 [P] In `frontend/src/app/register/page.tsx`, change the post-registration
      `router.push("/account")` to `router.push("/")` (FR-014)
- [ ] T025 Manually confirm that after a session expires or the user logs out, the homepage
      reverts to the guest view on next load rather than showing stale role-specific data (FR-013)
- [ ] T026 [P] Regression check: directly navigating (typed URL) to a role-restricted page (e.g.
      `/admin/shops`) as a mismatched or logged-out role is still blocked exactly as before this
      feature — no code change expected, this feature must not weaken existing enforcement
- [ ] T027 Run all 6 `quickstart.md` scenarios end to end against the running backend
      (`python manage.py runserver`) and frontend (`npm run dev`) dev servers (depends on all
      prior tasks)
- [ ] T028 `cd backend && pytest` — full suite passes, including the new
      `backend/tests/core/test_pagination.py`, with no regressions in any existing suite (depends
      on T004, T013, T017, T018)
- [ ] T029 Confirm FR-010 / constitution Principle VI: `git status`/`git diff` show no changes to
      `backend/apps/accounts/models.py` or `backend/apps/vendors/models.py`, no new migration
      files under either app's `migrations/`, and no change to `Shop.Status` choices or transition
      logic — this feature is presentation-only and must not touch the three-role model or the
      shop approval state machine (depends on all prior backend tasks: T002, T004, T013, T017,
      T018)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS every user story's backend pagination
  wiring (T004, T013, T017, T018).
- **User Stories (Phase 3-7)**: All depend on Foundational completion for their backend tasks;
  each story's `frontend/src/app/page.tsx` branch (T006, T011, T015, T021) is additive to the same
  file and should be implemented in story-priority order (US1 → US3 → US4 → US5) to avoid merge
  conflicts within that one file, even though the underlying data each branch reads is independent.
  US2 (nav) touches different files (`nav.tsx`, `layout.tsx`) and has no dependency on US1/US3/
  US4/US5's `page.tsx` branches.
- **Polish (Phase 8)**: Depends on all five user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational. No dependency on other stories.
- **US2 (P1)**: Depends only on Foundational (in practice, nothing — it doesn't touch pagination).
  Independent of US1/US3/US4/US5.
- **US3 (P2)**: Depends on Foundational; shares `listProducts` (T005) and the `page.tsx` file with
  US1, so is sequenced after US1 to avoid file conflicts, but is independently testable/verifiable
  once its own branch exists.
- **US4 (P2)**: Depends on Foundational; touches `orders/views.py`, `api-client.ts`, and its own
  `page.tsx` branch — sequenced after US3 for the same single-file reason, independently testable.
- **US5 (P3)**: Depends on Foundational; touches `vendors/views.py`, `orders/views.py` (same file
  as US4's T013 — different view class, no conflict), `api-client.ts`, and its own `page.tsx`
  branch — sequenced last, independently testable.

### Within Each User Story

- Backend pagination wiring before the frontend `api-client.ts` wrapper that calls it.
- `api-client.ts` wrapper before the `page.tsx` branch that uses it.
- Manual quickstart verification after the branch is built.

### Parallel Opportunities

- T001 (Setup) has no dependents besides T003 and can start immediately.
- T003 (pagination tests) can be written in parallel with nothing else in Phase 2 (T002 must land
  first, but T003 doesn't block T004+).
- US2 (T008-T010) can be built in parallel with US1 (T004-T007) by a second developer — different
  files entirely.
- Within US5, T017 and T018 (different files: `vendors/views.py` vs `orders/views.py`) can run in
  parallel. T019 and T020 both edit `api-client.ts` and are sequenced (T020 depends on T019), not
  parallel, to avoid a same-file conflict.
- T023 and T024 (Polish) touch different files and can run in parallel.
- T026 (regression check) has no dependencies and can run any time after Phase 2.

---

## Parallel Example: Foundational + User Story 1

```bash
# After T001 (Setup):
Task: "Create LimitedPageNumberPagination in backend/apps/core/pagination.py"   # T002

# After T002:
Task: "Add backend/tests/core/test_pagination.py"                               # T003 [P]
Task: "Set CatalogProductListView.pagination_class in backend/apps/catalog/views.py"  # T004

# After T004:
Task: "Add listProducts(limit?) to frontend/src/lib/api-client.ts"              # T005 [P]
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks pagination-dependent stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 against the real running app.
5. Demo the guest homepage.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → validate (quickstart Scenario 1) → demo (guest homepage, MVP).
3. US2 → validate (quickstart Scenario 2) → demo (nav on every page, every role).
4. US3 → validate (quickstart Scenario 3) → demo (Customer homepage).
5. US4 → validate (quickstart Scenario 4) → demo (Vendor homepage, all shop states).
6. US5 → validate (quickstart Scenario 5) → demo (Administrator homepage).
7. Phase 8 Polish (also exercises quickstart Scenario 6 and the Regression checks) → final review
   against the Constitution Check in plan.md.

Each story adds a new branch to the same `frontend/src/app/page.tsx` without touching the others'
branches, so earlier stories keep working as later ones are added — matches Principle V's
(Spec-Driven, Staged Delivery) requirement for reviewable, independently-verified chunks.

---

## Summary

- Total: 29 tasks (T001-T029) across Setup (1), Foundational (2), US1 (4), US2 (3), US3 (2), US4
  (4), US5 (6), Polish (7).
- Suggested MVP scope: User Story 1 only (guest homepage) — 7 tasks total including Setup and
  Foundational.

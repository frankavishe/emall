---

description: "Task list template for feature implementation"
---

# Tasks: Product Catalog

**Input**: Design documents from `/specs/002-product-catalog/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/catalog-api.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context commits this feature to `pytest` +
`pytest-django` + `factory_boy` + DRF `APIClient`, with the approval-gate enforcement (FR-002) and
validation rules (FR-012/FR-013) called out as the highest-value test targets — Success Criterion
SC-002 requires the gate to be provably server-side, not just asserted, so contract tests are
written per endpoint/behavior, first, before the implementation that makes them pass.

**Organization**: Tasks are grouped by user story (P1–P2 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Paths follow `plan.md`'s Project Structure: `backend/apps/catalog/`, `backend/tests/catalog/`,
  `frontend/src/app/{vendor/products,products}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new app and its non-Python-package prerequisites

- [x] T001 Add `Pillow>=12,<13` to `backend/requirements.txt` and install it into `backend/.venv`
      (required by Django's `ImageField` for `ProductImage`, research.md §1) — pinned to `>=12`
      rather than research.md's original `>=10` assumption because this venv runs Python 3.14.5,
      and Pillow only ships prebuilt Windows wheels for 3.14 from the 12.x series onward
- [x] T002 [P] Create the `catalog` Django app skeleton (`__init__.py`, `migrations/__init__.py`)
      at `backend/apps/catalog/`; register `"apps.catalog"` in `INSTALLED_APPS` in
      `backend/config/settings.py` — no `apps.py` added, matching the existing `apps.accounts`/
      `apps.vendors` convention in this codebase (no custom `AppConfig` needed)
- [x] T003 [P] Configure `MEDIA_ROOT` and `MEDIA_URL` in `backend/config/settings.py` and serve
      media locally in dev via `backend/config/urls.py` (research.md §1); `backend/media/` was
      already gitignored in the repo root `.gitignore`

**Checkpoint**: `catalog` app registered, boots with no models/routes yet, media serving
configured.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model and the approval-gate permission class every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — Constitution
Principle II (Vendor Approval Gate) is non-negotiable, so the permission class that enforces it
(T010) must exist before any create/publish endpoint is written, not be deferred to a later phase

- [x] T004 Create `Category` model in `backend/apps/catalog/models.py`: `name` (`CharField`,
      `unique=True`), `slug` (`SlugField`, `unique=True`) per data-model.md
- [x] T005 Create `Product` model in `backend/apps/catalog/models.py` per data-model.md: `shop`
      (`ForeignKey("vendors.Shop", related_name="products", on_delete=CASCADE)`), `category`
      (`ForeignKey(Category, related_name="products", on_delete=PROTECT, null=True)`), `name`
      (`CharField`, the only field required at creation), `description`
      (`TextField(blank=True, default="")`), `price`
      (`DecimalField(max_digits=10, decimal_places=2, null=True)`, must reject negative values —
      FR-012), `stock_quantity` (`PositiveIntegerField(null=True)` — non-negative by type when
      present, and the decrementable counter a future checkout feature needs per FR-015),
      `is_published` (`BooleanField`, `default=False`), `is_deleted` (`BooleanField`,
      `default=False`), `deleted_at` (`DateTimeField`, `null=True`), `created_at`
      (`auto_now_add=True`), `updated_at` (`auto_now=True`); added `UniqueConstraint(fields=
      ["shop", "name"])` (FR-013) and `CheckConstraint(condition=Q(price__gte=0) |
      Q(price__isnull=True))` (FR-012, using Django's current `condition=` kwarg); added
      `missing_fields_for_publish()` helper. **Correction found during Phase 3 implementation**:
      the original draft made `description`/`price`/`stock_quantity`/`category` `NOT NULL`, which
      made spec.md's "incomplete draft" Edge Case and FR-004's publish-time field check
      impossible to ever trigger (every product would already have all fields at creation). Made
      those four fields nullable/blank so a draft can genuinely be incomplete until publish is
      attempted; `data-model.md` updated to match. Migration `0001_initial` was regenerated
      (deleted and recreated, not amended) since nothing depended on the old schema yet (depends on
      T004)
- [x] T006 [P] Create `ProductImage` model in `backend/apps/catalog/models.py`: `product`
      (`ForeignKey(Product, related_name="images", on_delete=CASCADE)`), `image` (`ImageField`),
      `position` (`PositiveSmallIntegerField`, `default=0`) per data-model.md (depends on T005)
- [x] T007 Add a custom default manager (`ProductManager`) on `Product` in
      `backend/apps/catalog/models.py` that excludes `is_deleted=True` rows from every queryset, so
      no call site can accidentally leak a soft-deleted product (research.md §4, FR-014); also
      added `all_objects = models.Manager()` as an unfiltered escape hatch for future admin/debug
      access to soft-deleted rows (depends on T005)
- [x] T008 Generated and applied the `catalog` migration for `Category`/`Product`/`ProductImage`
      via `python manage.py makemigrations catalog && python manage.py migrate` (depends on T004,
      T005, T006, T007)
- [x] T009 [P] Created `backend/apps/catalog/migrations/0002_seed_categories.py` (a
      `RunPython` data migration, reversible) seeding Electronics, Fashion, Home & Kitchen, Books,
      Beauty with slugs (research.md §3); applied and verified via `manage.py shell` (depends on
      T008)
- [x] T010 [P] Implemented `IsApprovedShopOwnerForProduct` in
      `backend/apps/catalog/permissions.py`: `has_object_permission` returns `True` only when
      `obj.shop.status == Shop.Status.APPROVED and obj.shop.owner_id == request.user.id`
      (research.md §5, FR-002, FR-006) (depends on T005)

**Checkpoint**: Foundation ready — migrations apply cleanly, `Category` seed data exists,
`Product`/`ProductImage` models and the approval-gate permission class exist. User story
implementation can now begin.

---

## Phase 3: User Story 1 - Vendor manages products in an approved shop (Priority: P1) 🎯 MVP

**Goal**: A Vendor with an APPROVED shop can create, edit, publish, unpublish, and delete product
listings scoped strictly to shop(s) they own.

**Independent Test**: Log in as a Vendor with an APPROVED shop, create a product via
`POST /api/vendor/products/`, confirm it doesn't appear in `GET /api/catalog/products/` until
published, publish it via `POST /api/vendor/products/{id}/publish/`, confirm it now appears, edit
a field, then unpublish it and confirm it disappears from the public catalog again.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T011 [P] [US1] Contract test `POST /api/vendor/products` — `201` draft/unpublished for an
      APPROVED shop the Vendor owns; `403` for a shop the Vendor doesn't own; `400` negative price
      (FR-012), negative stock_quantity (FR-012), duplicate name within the same shop (FR-013) in
      `backend/tests/catalog/test_vendor_product_create.py` (5 tests)
- [x] T012 [P] [US1] Contract test `PATCH /api/vendor/products/{id}` — updates any field
      regardless of `is_published` state; `403` if the requester isn't the owning Vendor (FR-003)
      in `backend/tests/catalog/test_vendor_product_update.py` (3 tests)
- [x] T013 [P] [US1] Contract test `POST /api/vendor/products/{id}/publish` and `.../unpublish` —
      publish requires `description`/`price`/`stock_quantity`/`category` present (not `name`,
      which is always required to even create the row — see T005's correction), else `400` with a
      `missing_fields` list; unpublish leaves the row intact in the DB (public-catalog visibility
      check itself lives in Phase 5, not yet built) (FR-004, FR-005, Edge Cases) in
      `backend/tests/catalog/test_vendor_product_publish.py` (3 tests)
- [x] T014 [P] [US1] Contract test `DELETE /api/vendor/products/{id}` — soft-deletes (row
      persists in `Product.all_objects` with `is_deleted=True`), disappears from the Vendor's own
      list (FR-014) in `backend/tests/catalog/test_vendor_product_delete.py` (2 tests)
- [x] T015 [P] [US1] Contract test `GET /api/vendor/products` — a Vendor with multiple shops only
      sees products belonging to shops they own, across all of them (FR-006) in
      `backend/tests/catalog/test_vendor_product_list.py` (1 test). **14 tests total for T011–T015,
      all passing**; also verified live via the browser (see below) and via direct `curl` calls for
      the approval-gate and incomplete-draft-publish scenarios.

### Implementation for User Story 1

- [x] T016 [US1] Implemented `VendorProductWriteSerializer` in `backend/apps/catalog/serializers.py`:
      accepts `shop_id`, `name`, `description`, `price`, `stock_quantity`, `category` (slug),
      `images`; validates `price >= 0` / `stock_quantity >= 0` (FR-012) and `(shop, name)`
      uniqueness (FR-013) in `validate()`; on create, validates `shop_id` ownership+approval and
      raises `PermissionDenied` (403) rather than a field error (depends on T005, T006)
- [x] T017 [US1] Implemented `VendorProductListSerializer` (read) in
      `backend/apps/catalog/serializers.py`. **Deviation from contracts/catalog-api.md**: also
      includes `description` (the contract's list example omits it) so the edit page can prefill a
      form from this same list response without a separate per-product detail endpoint — noted
      inline in the serializer's docstring (depends on T005, T006)
- [x] T018 [US1] Implemented `VendorProductListCreateView` + `VendorProductDetailView` in
      `backend/apps/catalog/views.py`. **Deviation from the original "DRF router for
      VendorProductViewSet" sketch**: built as plain `ListCreateAPIView`/`APIView` classes with
      explicit `path()` entries instead — matches this codebase's existing convention in
      `apps/vendors/views.py`/`urls.py` (no routers/ViewSets used anywhere else in the project).
      **Also split the permission model**: create uses `IsApprovedShopOwnerForProduct` (ownership +
      APPROVED, via serializer `validate()`); PATCH/DELETE use a new, simpler `IsProductOwner`
      (ownership only) added to `apps/catalog/permissions.py` — FR-003/FR-014 don't require the
      shop to still be APPROVED to edit/delete, only `IsApprovedShopOwnerForProduct`'s original
      scope (create/publish, FR-002/FR-004) does; `destroy` soft-deletes (depends on T010, T016,
      T017)
- [x] T019 [US1] Implemented `VendorProductPublishView`/`VendorProductUnpublishView` in
      `backend/apps/catalog/views.py`: publish uses `IsApprovedShopOwnerForProduct` and
      `Product.missing_fields_for_publish()` (added on the model in T005), returning `400
      {"missing_fields": [...]}`; unpublish uses `IsProductOwner` (FR-005) (depends on T018)
- [x] T020 [US1] Wired `backend/apps/catalog/urls.py` (`vendor_urlpatterns`, explicit `path()`
      entries, no trailing slashes — matching `apps/vendors/urls.py`) and included it a second time
      under the existing `path("api/vendor/", ...)` prefix in `backend/config/urls.py` (Django
      tries multiple url-confs at the same prefix in order; no conflict with `apps.vendors.urls`'s
      own `products`-free `shops` path) (depends on T018, T019)
- [x] T021 [P] [US1] Built `frontend/src/app/vendor/products/page.tsx`: lists the logged-in
      Vendor's own products, publish/unpublish/delete actions, link to create a new product;
      styled to match the existing `admin/shops/page.tsx` list pattern
- [x] T022 [P] [US1] Built `frontend/src/app/vendor/products/new/page.tsx`: create-product form
      posting `multipart/form-data` to `POST /api/vendor/products`. **Pulled forward `GET
      /api/catalog/categories` (originally T035, Phase 5/US3) since the category picker needs it
      and there's no vendor-only equivalent** — added `CategorySerializer` + `CategoryListView`
      (public, `AllowAny`) now; Phase 5 will find T035 already done
- [x] T023 [US1] Built `frontend/src/app/vendor/products/[id]/edit/page.tsx`: edit form
      pre-populated from the Vendor's product list data (via T017's `description`-inclusive
      serializer), `PATCH`s on submit, with a Publish/Unpublish toggle (depends on T021, T022)

**Bugs found and fixed while running this end-to-end (Constitution Principle V — "run for real")**:
1. `frontend/src/lib/api-client.ts`'s `apiFetch` always forced `Content-Type: application/json`
   whenever a body was present, which would have silently broken every `multipart/form-data` image
   upload (wrong/missing boundary). Fixed to skip that header when `body instanceof FormData`.
2. `frontend/src/lib/auth-context.tsx`'s `login()` set `user` directly from the login response,
   which (unlike `/api/auth/me`) never includes `shops` — a Vendor who logged in (as opposed to
   registering fresh) saw "No shops yet" on `/account` and had no APPROVED shop available to pick
   from on `/vendor/products/new`, even though the shop existed. This is a **pre-existing bug from
   001-accounts-auth**, not something this feature introduced, but it directly blocked this
   feature's UI. Fixed `login()` to call `refreshUser()` (hits `/api/auth/me`) instead of trusting
   the login response's `user` field.

**Manually verified live** (real Postgres + `runserver` + `next dev`, via `claude-in-chrome`):
logged in as a seeded Vendor with an APPROVED shop → created "USB-C Cable" as a draft → confirmed
"Status: Draft" on the edit page → clicked Publish → confirmed "Status: Published" and the button
flipped to Unpublish → confirmed the same on the list page. Also verified via direct `curl` (not
the UI): creating a product under a freshly-seeded PENDING shop for the same Vendor → `403`;
creating a bare `{name, shop_id}`-only draft → `201`, then publishing it → `400` with
`{"missing_fields": ["description","price","stock_quantity","category"]}`, exactly matching
spec.md's Edge Case. Test data cleaned up afterward; full suite re-run clean (78 passed).

**Checkpoint**: User Story 1 is fully functional and independently testable — Vendor
create/edit/publish/unpublish/delete works end to end against real Postgres, backend and frontend.

---

## Phase 4: User Story 2 - Unapproved or rejected shop is blocked (Priority: P1)

**Goal**: Product creation/publishing under a PENDING or REJECTED shop is rejected server-side,
regardless of what any client sends — proven independent of the UI.

**Independent Test**: Attempt to create or publish a product under a PENDING or REJECTED shop via
a direct API call (not the UI) and confirm the server rejects it with `403`.

> The enforcement mechanism itself (`IsApprovedShopOwnerForProduct`, T010) and its wiring into the
> create/publish endpoints (T018, T019) were necessarily built during Foundational/US1 — Principle
> II is non-negotiable, so product creation could not have shipped without it. This phase's job is
> to lock that behavior in with dedicated tests covering exactly the scenarios spec.md calls out,
> and to close the one residual gap (re-checking at publish time, not only at creation time).
>
> **Status as of the end of Phase 3**: the gate was already manually proven via direct `curl` calls
> (403 for a PENDING shop's create attempt, 200 for the same Vendor's APPROVED shop) while running
> US1 end-to-end — see the "Manually verified live" note above. T024–T027 below (committing that as
> permanent, automated `pytest` coverage) are still open.

### Tests for User Story 2 ⚠️

- [ ] T024 [P] [US2] Contract test: `POST /api/vendor/products/` and
      `POST /api/vendor/products/{id}/publish/` against a PENDING shop the Vendor owns → `403`
      with a clear "shop not approved" message, no product created/published (FR-002) in
      `backend/tests/catalog/test_shop_approval_gate.py`
- [ ] T025 [P] [US2] Contract test: same two calls against a REJECTED shop → `403`, same message
      (FR-002) in `backend/tests/catalog/test_shop_approval_gate.py`
- [ ] T026 [US2] Contract test: a Vendor who owns one APPROVED shop and one PENDING shop can
      create/publish under the APPROVED shop while the PENDING shop still `403`s in the same test
      run, proving the gate is enforced per-shop, not per-account (spec User Story 2 Scenario 3)
      in `backend/tests/catalog/test_shop_approval_gate.py` (depends on T024, T025)

### Implementation for User Story 2

- [ ] T027 [US2] Verify (and fix if T024–T026 expose a gap) that `shop.status` is re-checked on
      *both* the create serializer's `shop_id` validation (T016) and the `publish` action (T019) —
      not only at creation time — since a shop's status could change between a product's creation
      and its publish (contracts/catalog-api.md) in `backend/apps/catalog/serializers.py` /
      `backend/apps/catalog/views.py` (depends on T018, T019, T024, T025, T026)

**Checkpoint**: Both P1 stories done — the approval gate is proven server-side via direct API
calls independent of the UI (SC-002).

---

## Phase 5: User Story 3 - Customer browses, searches, filters the catalog (Priority: P2)

**Goal**: Customers/visitors can browse, keyword-search, and category/price-filter the published
catalog, and view a single product's detail page.

**Independent Test**: With products published across two shops, browse the full catalog, search
by a keyword matching one product, filter by category and price range, and open a product's detail
page — all unauthenticated.

### Tests for User Story 3 ⚠️

- [ ] T028 [P] [US3] Contract test `GET /api/catalog/products/` — returns only published,
      non-deleted products from APPROVED shops; a `q` with no matches returns `200` with
      `"results": []`, not an error (FR-007, FR-011, Edge Cases) in
      `backend/tests/catalog/test_catalog_list.py`
- [ ] T029 [P] [US3] Contract test `GET /api/catalog/products/` with `q`, `category`,
      `min_price`/`max_price` — each filter works alone and combined with the others (FR-008,
      FR-009) in `backend/tests/catalog/test_catalog_filters.py`
- [ ] T030 [P] [US3] Contract test `GET /api/catalog/products/{id}/` — full detail shape including
      `stock_status`; returns the same `404` (not a different status) for a nonexistent,
      unpublished, soft-deleted, or non-APPROVED-shop product, so none are distinguishable to an
      anonymous caller (FR-010, FR-011) in `backend/tests/catalog/test_catalog_detail.py`
- [ ] T031 [P] [US3] Contract test: a published product with `stock_quantity=0` still appears in
      both list (`in_stock: false`) and detail (`stock_status: "out_of_stock"`) rather than being
      hidden (FR-011, Edge Cases) in `backend/tests/catalog/test_catalog_stock_status.py`

### Implementation for User Story 3

- [ ] T032 [US3] Implement `CatalogProductListSerializer` and `CatalogProductDetailSerializer`
      (read-only) in `backend/apps/catalog/serializers.py` matching contracts/catalog-api.md's
      public shapes; derive `in_stock`/`stock_status` from `stock_quantity > 0`, never expose the
      raw count (FR-011) (depends on T005, T006)
- [ ] T033 [US3] Implement `CatalogProductListView` in `backend/apps/catalog/views.py`: base
      queryset `Product.objects.filter(is_published=True, shop__status=Shop.Status.APPROVED)`
      (soft-deleted rows already excluded by T007's manager); applies `q`
      (`Q(name__icontains=...) | Q(description__icontains=...)`), `category` (exact slug),
      `min_price`/`max_price` (`gte`/`lte` on `price`) query params (research.md §2); paginated;
      `AllowAny` (depends on T032)
- [ ] T034 [US3] Implement `CatalogProductDetailView` in `backend/apps/catalog/views.py`: same base
      queryset as T033, `get_object_or_404` so a hidden/nonexistent product returns a uniform
      `404`; `AllowAny` (depends on T032)
- [ ] T035 [P] [US3] Implement `CategoryListView` (read-only, `AllowAny`) in
      `backend/apps/catalog/views.py` returning all seeded categories (depends on T004, T009)
- [ ] T036 [US3] Wire the public `urlpatterns` (`products/`, `products/<id>/`, `categories/`) in
      `backend/apps/catalog/urls.py` and include under `/api/catalog/` in `backend/config/urls.py`
      (depends on T033, T034, T035)
- [ ] T037 [P] [US3] Build `frontend/src/app/products/page.tsx`: catalog grid with a search box and
      category/price filter controls, calling `GET /api/catalog/products/` (depends on T036)
- [ ] T038 [P] [US3] Build `frontend/src/app/products/[id]/page.tsx`: product detail page calling
      `GET /api/catalog/products/{id}/`, showing price, images, stock status, and selling shop name
      (depends on T036)

**Checkpoint**: All three user stories independently functional — the full Product Catalog feature
works end to end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T039 [P] Confirm `VendorProductViewSet` (T018) and `CatalogProductListView` (T033)
      pagination page sizes are sane per Constitution "Resource Utilization" in
      `backend/apps/catalog/views.py`
- [ ] T040 Run all 5 `quickstart.md` scenarios end to end against real PostgreSQL with migrations
      applied and at least one seeded APPROVED + one PENDING shop, per Constitution Principle V
- [ ] T041 [P] Security/validation review pass: confirm image uploads are restricted to image
      content types and a bounded file size at the serializer layer, and that `shop_id`/ownership
      cannot be spoofed via a crafted `PATCH` body (Constitution Principle I/III) in
      `backend/apps/catalog/serializers.py`
- [ ] T042 [P] Extend `backend/README.md` with catalog setup notes: the `Pillow` dependency, media
      settings, and the category seed migration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (Category/
  Product/ProductImage models and the approval-gate permission are used by every story)
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories
  - US2 (P1) depends on US1's create/publish endpoints (T018, T019) existing — it tests and
    hardens behavior that had to be built alongside them, not new endpoints of its own
  - US3 (P2) depends only on Foundational (the `Product`/`Category` models) — it does not require
    US1/US2 to be complete, though in practice some published products (from US1) are needed to
    demo it meaningfully
  - In practice: implement in priority order **US1 → US2 → US3** — each is still an independently
    testable increment per its own Independent Test above
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and failing before implementation
- Models (Foundational) before serializers
- Serializers before views
- Views before URL wiring
- Backend endpoint before its corresponding frontend page
- Story's backend fully working before its frontend is wired to it

### Parallel Opportunities

- Setup tasks marked [P] (T002, T003) can run in parallel once T001 lands
- Within Foundational: T004 must precede T005; T005 must precede T006/T007; T009 and T010 are
  independent of each other and can run in parallel once T008 lands
- All contract tests within a story (marked [P]) can run in parallel with each other
- Frontend page tasks marked [P] can run in parallel with each other once the endpoint(s) they call
  exist
- US3's backend work (T032–T036) can proceed in parallel with US1/US2 once Foundational is done,
  since it only depends on the Foundational models — useful if staffed with multiple developers

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test POST /api/vendor/products/ in backend/tests/catalog/test_vendor_product_create.py"
Task: "Contract test PATCH /api/vendor/products/{id}/ in backend/tests/catalog/test_vendor_product_update.py"
Task: "Contract test publish/unpublish in backend/tests/catalog/test_vendor_product_publish.py"
Task: "Contract test DELETE /api/vendor/products/{id}/ in backend/tests/catalog/test_vendor_product_delete.py"
Task: "Contract test GET /api/vendor/products/ in backend/tests/catalog/test_vendor_product_list.py"

# Launch the two independent frontend pages together:
Task: "Build frontend/src/app/vendor/products/page.tsx"
Task: "Build frontend/src/app/vendor/products/new/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 independently
5. Demo: Vendor can create, publish, edit, and unpublish a product

### Incremental Delivery

1. Setup + Foundational → data model and approval-gate permission ready
2. US1 → validate (quickstart Scenario 1) → demo (vendor product management MVP)
3. US2 → validate (Scenario 2, via direct API calls) → demo (approval gate proven server-side)
4. US3 → validate (Scenario 3) → demo (public catalog browse/search/filter)
5. Phase 6 polish (also exercises Scenarios 4 and 5) → final review against Constitution before
   considering the feature done

### Constitution alignment (Principle V: Spec-Driven, Staged Delivery)

Per the Constitution, implementation MUST proceed in reviewable chunks — **one phase at a time**,
each run for real (migrations applied, endpoints exercised via the DRF browsable API or the actual
Next.js dev server) and reviewed before starting the next. Do not run `/speckit-implement` to
generate all 42 tasks unattended; implement and check off one phase (ideally one user story) at a
time.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability back to spec.md
- Each user story is independently completable and testable per its Independent Test statement
- Verify contract tests fail before implementing the view/serializer that makes them pass
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
- Total: 42 tasks (T001–T042) across Setup (3), Foundational (7), US1 (13), US2 (4), US3 (11),
  Polish (4)

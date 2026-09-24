---

description: "Task list template for feature implementation"
---

# Tasks: Product Feedback & Reviews

**Input**: Design documents from `/specs/005-product-feedback/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/feedback-api.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context commits this feature to `pytest` +
`pytest-django` + `factory_boy` + DRF `APIClient`, the same testing commitment 001-004 already
made, applied to the new `Review` entity, the DELIVERED-purchase eligibility gate (FR-001/FR-002),
the upsert/uniqueness guarantee (FR-003), and the queryset-level Vendor/Administrator scoping
(FR-007/FR-009/FR-010).

**Organization**: Tasks are grouped by user story (P1-P3 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US4)
- Paths follow `plan.md`'s Project Structure: this feature adds one new Django app,
  `backend/apps/feedback/` (+ `backend/tests/feedback/`); `backend/apps/catalog/serializers.py`
  is extended in place; frontend work is in
  `frontend/src/app/{products/[id],vendor/reviews,admin/reviews}/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the new Django app this feature lives in

- [X] T001 Create the `backend/apps/feedback/` Django app (`__init__.py`, `apps.py`, `models.py`,
      `migrations/__init__.py`), matching the existing app layout (e.g. `backend/apps/vendors/`)
- [X] T002 Add `"apps.feedback"` to `INSTALLED_APPS` in `backend/config/settings.py`
- [X] T003 [P] Add `OrderItemFactory` to `backend/tests/factories.py` (product, order via
      `SubFactory`, `quantity`, `status=OrderItem.Status.DELIVERED` by default) — fills the gap
      004-order-fulfillment's tests worked around (research.md §7); needed by every story's tests
      below to set up DELIVERED/non-DELIVERED fixtures quickly

**Checkpoint**: `feedback` app exists and is installed; test fixtures ready. Foundational work can
begin.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the `Review` model and the purchase-eligibility check every user story depends
on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — User Story 1's write
path, User Story 2's read/aggregate, and User Stories 3-4's scoped list views all read or write
through this model

- [X] T004 Create `Review` model in `backend/apps/feedback/models.py` per data-model.md:
      `customer` (`ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE,
      related_name="reviews")`), `product` (`ForeignKey("catalog.Product", on_delete=CASCADE,
      related_name="reviews")`), `rating` (`PositiveSmallIntegerField`, must be "1-5 inclusive,
      enforced by a `CheckConstraint`"), `comment` (`TextField(blank=True, default="")`),
      `created_at` (`auto_now_add=True`), `updated_at` (`auto_now=True`); add
      `UniqueConstraint(fields=["customer", "product"],
      name="unique_review_per_customer_product")` and `CheckConstraint(condition=Q(rating__gte=1)
      & Q(rating__lte=5), name="review_rating_range")` in `Meta.constraints`
- [X] T005 Generate and apply the `feedback` migration (`python manage.py makemigrations feedback
      && python manage.py migrate`) (depends on T001, T002, T004)
- [X] T006 [P] Add `ReviewFactory` to `backend/tests/factories.py` (customer, product via
      `SubFactory`, `rating=5`, `comment="Great product."`) (depends on T004)
- [X] T007 [P] Implement `has_delivered_purchase(customer, product)` in
      `backend/apps/feedback/permissions.py`: returns
      `OrderItem.objects.filter(order__customer=customer, product=product,
      status=OrderItem.Status.DELIVERED).exists()` (FR-001, FR-002; research.md §2 — re-checked
      live on every call, never cached) (depends on T001)

**Checkpoint**: `Review` schema exists and is migrated; eligibility check and test factories are
ready. User story implementation can now begin.

---

## Phase 3: User Story 1 - Customer leaves a rating and review on a purchased product (Priority: P1) 🎯 MVP

**Goal**: A Customer with a DELIVERED order line for a product can submit a 1-5 star rating and
optional written comment for it, update it later, and delete it — one review per (Customer,
Product) pair.

**Independent Test**: As a Customer with an `OrderItem` for a product at `DELIVERED` status,
`POST /api/feedback/products/{product_id}/review/` with a rating (and optional comment) and
confirm it is saved and attributed to that customer; confirm a Customer with no such order line is
rejected.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [X] T008 [P] [US1] Contract test `POST /api/feedback/products/{product_id}/review/` with rating
      + comment — `201`, review saved and attributed to the requesting customer (FR-001,
      Acceptance Scenario 1) in `backend/tests/feedback/test_customer_review_submit.py`
- [X] T009 [P] [US1] Contract test `POST .../review/` with rating only, no `comment` — `201`,
      `comment` defaults to `""` (FR-001 "comment optional", Acceptance Scenario 2) in the same
      file as T008
- [X] T010 [P] [US1] Contract test `POST .../review/` from a Customer with no DELIVERED
      `OrderItem` for that product — `403`, no review row created (FR-002, Acceptance Scenario 3,
      SC-002) in `backend/tests/feedback/test_customer_review_eligibility.py`
- [X] T011 [P] [US1] Contract test repeat `POST .../review/` by the same Customer for the same
      product — second call returns `200` (not `201`) with the same review `id` as the first,
      updated rating/comment; at most one `Review` row exists for that (customer, product) pair
      (FR-003, Acceptance Scenario 4/5, SC-006) in
      `backend/tests/feedback/test_customer_review_upsert.py`
- [X] T012 [P] [US1] Contract test `DELETE /api/feedback/products/{product_id}/review/` — `204`
      and the review is gone for the owning Customer; a second `DELETE` returns `404`; a Customer
      with no review on that product also gets `404` (FR-004) in
      `backend/tests/feedback/test_customer_review_delete.py`

### Implementation for User Story 1

- [X] T013 [US1] Implement `ReviewWriteSerializer` (`rating` required `IntegerField(min_value=1,
      max_value=5)`, `comment` optional `CharField(required=False, allow_blank=True, default="")`)
      in `backend/apps/feedback/serializers.py` (depends on T004)
- [X] T014 [US1] Implement `CustomerReviewView` in `backend/apps/feedback/views.py`: `IsCustomer`;
      `post()` calls `has_delivered_purchase()` (T007), raising `403` if `False`, then
      `Review.objects.update_or_create(customer=request.user, product=product,
      defaults={"rating": ..., "comment": ...})` via `ReviewWriteSerializer`, returning `201` on
      create / `200` on update; `delete()` does `get_object_or_404(Review, customer=request.user,
      product=product)` then deletes it, returning `204` (depends on T007, T013)
- [X] T015 [US1] Wire `urlpatterns` (`feedback/products/<int:product_id>/review`) in
      `backend/apps/feedback/urls.py`; include at `api/` in `backend/config/urls.py` (mounting the
      full `/api/feedback/...` path) alongside the existing `apps.cart.urls`/checkout includes
      (depends on T014)
- [X] T016 [US1] Add `submitReview(productId, { rating, comment })` /
      `deleteReview(productId)` calls to `frontend/src/lib/api-client.ts`, matching the
      `checkout`/`listOrders` wrapper-function precedent already in that file (depends on T015)
- [X] T017 [US1] Build a review submission form (star input + optional comment textarea) in
      `frontend/src/app/products/[id]/page.tsx`, shown to any logged-in Customer viewing the
      product; on submit calls `submitReview`; on a `403` response shows "You can only review
      products you have received" rather than a generic error (depends on T016)

**Checkpoint**: User Story 1 is fully functional and independently testable — a Customer can
submit, update, and delete a review, backend and frontend.

---

## Phase 4: User Story 2 - Shoppers see reviews on the product detail page (Priority: P1)

**Goal**: Any shopper, logged in or not, sees a product's reviews and aggregate rating on its
detail page; the browse/list page shows the aggregate rating.

**Independent Test**: As any shopper (including logged-out), `GET /api/catalog/products/{id}/` for
a reviewed product and confirm `reviews`, `average_rating`, and `review_count` are present and
correct; confirm a product with no reviews returns an empty/zero state rather than an error.

### Tests for User Story 2 ⚠️

- [X] T018 [P] [US2] Contract test `GET /api/catalog/products/{id}/` (no `Authorization` header)
      for a product with reviews — response includes `average_rating`, `review_count`, and a
      `reviews` array with each review's rating, comment, reviewing customer's display name, and
      timestamp (FR-005, FR-006, Acceptance Scenario 1) in
      `backend/tests/feedback/test_catalog_product_reviews_display.py`
- [X] T019 [P] [US2] Contract test `GET /api/catalog/products/{id}/` for a product with zero
      reviews — `average_rating: null`, `review_count: 0`, `reviews: []`, no error (FR-006,
      Acceptance Scenario 2) in the same file as T018
- [X] T020 [P] [US2] Contract test `GET /api/catalog/products/` (list endpoint) — each result
      includes `average_rating`/`review_count` but no `reviews` array (contracts/feedback-api.md:
      full review list is detail-only) in the same file as T018
- [X] T021 [P] [US2] Contract test: after a new review is submitted (T014) or an existing one
      updated/removed, the next `GET /api/catalog/products/{id}/` reflects the recalculated
      `average_rating`/`review_count` with no separate recalculation step (FR-006, Acceptance
      Scenario 3) in the same file as T018

### Implementation for User Story 2

- [X] T022 [US2] Implement `ReviewDisplaySerializer` (`id`, `customer_display_name` [derived from
      `review.customer`], `rating`, `comment`, `created_at`) in
      `backend/apps/feedback/serializers.py` (depends on T004)
- [X] T023 [US2] Extend `CatalogProductDetailSerializer` in `backend/apps/catalog/serializers.py`
      with `average_rating`/`review_count` (`SerializerMethodField`s computing
      `obj.reviews.aggregate(Avg("rating"), Count("id"))`, research.md §4) and `reviews`
      (`ReviewDisplaySerializer(obj.reviews.select_related("customer").order_by("-created_at"),
      many=True).data`) (depends on T022)
- [X] T024 [US2] Extend `CatalogProductListSerializer` in `backend/apps/catalog/serializers.py`
      with the same `average_rating`/`review_count` fields as T023, no `reviews` field (depends on
      T022)
- [X] T025 [US2] Build a reviews section (average-rating badge, review count, list of
      rating+comment+reviewer name) on `frontend/src/app/products/[id]/page.tsx`, and an
      `average_rating` badge on the product grid item in `frontend/src/app/products/page.tsx`,
      using a shared star-rating display component in `frontend/src/components/` (depends on
      T023, T024)

**Checkpoint**: User Stories 1 AND 2 both work — a submitted review is immediately visible to any
shopper with a correct aggregate rating.

---

## Phase 5: User Story 3 - Vendor views feedback on their own shop's products (Priority: P2)

**Goal**: A Vendor can see every review left on their own shop's products, across all their
products, in one place — read-only.

**Independent Test**: As a Vendor with an APPROVED shop and reviewed products,
`GET /api/vendor/reviews/` and confirm every review on their own products appears, and that no
review belonging to another vendor's shop appears.

### Tests for User Story 3 ⚠️

- [X] T026 [P] [US3] Contract test `GET /api/vendor/reviews/` — returns reviews on products
      belonging to the requester's own shop(s) only, paginated, each including which product it's
      for; `403` for a non-Vendor caller (FR-007, Acceptance Scenario 1) in
      `backend/tests/feedback/test_vendor_review_list.py`
- [X] T027 [P] [US3] Contract test cross-vendor isolation — Vendor B's `GET /api/vendor/reviews/`
      never includes a review on Vendor A's product, and vice versa (FR-009, Acceptance Scenario
      3, SC-004) in the same file as T026
- [X] T028 [P] [US3] Contract test: `PATCH`/`POST`/`DELETE` on `/api/vendor/reviews/` are all
      rejected — vendor visibility is read-only (FR-008, Acceptance Scenario 2) in the same file
      as T026

### Implementation for User Story 3

- [X] T029 [US3] Implement `VendorReviewSerializer` (`id`, `product` [`id`, `name`],
      `customer_display_name`, `rating`, `comment`, `created_at`) in
      `backend/apps/feedback/serializers.py` (depends on T004)
- [X] T030 [US3] Implement `VendorReviewListView` in `backend/apps/feedback/views.py`: `IsVendor`;
      queryset `Review.objects.filter(product__shop__owner=request.user)
      .select_related("product", "customer")` (queryset-level scoping, research.md §5) (depends
      on T029)
- [X] T031 [US3] Wire `vendor_urlpatterns` (`vendor/reviews`) in `backend/apps/feedback/urls.py`;
      include at `api/vendor/` in `backend/config/urls.py` alongside the existing
      `apps.vendors.urls`/`apps.catalog.urls`/`apps.orders.urls` vendor includes (depends on T030)
- [X] T032 [P] [US3] Add `listVendorReviews(page)` call to `frontend/src/lib/api-client.ts`
      (depends on T031)
- [X] T033 [US3] Build `frontend/src/app/vendor/reviews/page.tsx`: read-only paginated list of
      feedback on the Vendor's own products (depends on T032)

**Checkpoint**: User Stories 1-3 independently functional — Vendors can read feedback on their own
products without seeing or altering anyone else's.

---

## Phase 6: User Story 4 - Administrator moderates inappropriate reviews (Priority: P3)

**Goal**: An Administrator can view every review across all products/shops and remove any single
one; removal is reflected immediately everywhere the review was visible.

**Independent Test**: As an Administrator, `GET /api/admin/reviews/`, locate a review, `DELETE` it,
and confirm it no longer appears on the product page, in the Vendor's feedback view, or in the
product's rating aggregate.

### Tests for User Story 4 ⚠️

- [X] T034 [P] [US4] Contract test `GET /api/admin/reviews/` — lists every review across all
      products/shops, paginated, each including product, shop, and reviewing customer identity;
      `403` for a non-Administrator caller (FR-010, Acceptance Scenario 2) in
      `backend/tests/feedback/test_admin_review_list.py`
- [X] T035 [P] [US4] Contract test `DELETE /api/admin/reviews/{review_id}/` — `204`, review row
      removed; a second `DELETE` on the same id returns `404` (FR-011, FR-012) in
      `backend/tests/feedback/test_admin_review_delete.py`
- [X] T036 [P] [US4] Contract test post-delete effects — after an Administrator removes a review,
      `GET /api/catalog/products/{id}/`'s `average_rating`/`review_count`/`reviews` no longer
      include it (T023/T024 recomputed on read, no manual step), `GET /api/vendor/reviews/` for
      the owning Vendor no longer includes it, and the previously-reviewing Customer can
      successfully `POST /api/feedback/products/{id}/review/` again as a fresh (not restored)
      review, given they still have a DELIVERED order line (FR-011, Acceptance Scenario 1/3,
      SC-005) in `backend/tests/feedback/test_admin_review_delete_effects.py`

### Implementation for User Story 4

- [X] T037 [US4] Implement `AdminReviewSerializer` (`id`, `product` [`id`, `name`], `shop` [`id`,
      `name`], `customer` [`id`, `email`], `rating`, `comment`, `created_at`) in
      `backend/apps/feedback/serializers.py` (depends on T004)
- [X] T038 [US4] Implement `AdminReviewListView` and `AdminReviewDeleteView` in
      `backend/apps/feedback/views.py`: `IsAdministrator`; queryset
      `Review.objects.select_related("product__shop", "customer")` across every shop, paginated;
      delete view does `get_object_or_404(Review, pk=review_id).delete()` returning `204` (FR-010,
      FR-011, FR-012) (depends on T037)
- [X] T039 [US4] Wire `admin_urlpatterns` (`admin/reviews`, `admin/reviews/<int:review_id>`) in
      `backend/apps/feedback/urls.py`; include at `api/admin/` in `backend/config/urls.py`
      alongside the existing `apps.vendors.urls`/`apps.orders.urls` admin includes (depends on
      T038)
- [X] T040 [P] [US4] Add `listAdminReviews(page)` / `deleteReviewAsAdmin(reviewId)` calls to
      `frontend/src/lib/api-client.ts` (depends on T039)
- [X] T041 [US4] Build `frontend/src/app/admin/reviews/page.tsx`: paginated list across all
      shops/products with a remove action per review (depends on T040)

**Checkpoint**: All four user stories independently functional — the full feedback loop (submit →
display → vendor read → admin moderate) works end to end.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T042 [P] Confirm `VendorReviewListView`'s and `AdminReviewListView`'s (T030, T038)
      pagination page size matches the existing `PAGE_SIZE = 20` DRF default (`config/settings.py`)
      that `VendorProductListCreateView`/`AdminShopListView` already inherit (Constitution
      "Resource Utilization") in `backend/apps/feedback/views.py`
- [X] T043 Run all 5 `quickstart.md` scenarios end to end against real PostgreSQL with migrations
      applied, per Constitution Principle V
- [X] T044 [P] Security/validation review pass: confirm `CustomerReviewView` always re-queries
      live `OrderItem` status via `has_delivered_purchase()` rather than trusting any
      client-supplied eligibility claim; confirm `VendorReviewListView`'s and
      `AdminReviewListView`'s querysets filter by `request.user`'s own shop ownership or
      `IsAdministrator` at the queryset level, never only in a serializer (Constitution Principle
      I) across `backend/apps/feedback/`
- [X] T045 [P] Extend `backend/README.md` with a "Product Feedback & Reviews" section: the new
      `feedback` app, the `Review` model's one-per-customer-per-product constraint, and the new
      `/api/feedback/...`, `/api/vendor/reviews`, `/api/admin/reviews` endpoints

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories — `Review`'s
  schema and `has_delivered_purchase()` are read or written by every later phase
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories
  - US2 (P1) depends on Foundational only for its data to display; independently testable once
    at least one review exists (via US1 or a factory-created fixture in its own tests)
  - US3 (P2) depends on Foundational only (reads `Review` rows directly in its own tests via
    `ReviewFactory`, not on US1's endpoint)
  - US4 (P3) depends on Foundational only, same reasoning as US3
  - In practice: implement in priority/dependency order **US1 → US2 → US3 → US4** — each is still
    an independently testable increment per its own Independent Test above
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and failing before implementation
- Model/migration (Foundational) before serializers
- Serializers before views
- Views before URL wiring
- Backend endpoint before its corresponding frontend page

### Parallel Opportunities

- Foundational: T006 (`ReviewFactory`) and T007 (`has_delivered_purchase`) are independent files/
  concerns, both depend only on T004, and can run in parallel
- All contract tests within a story (marked [P]) can run in parallel with each other
- US2's serializer extensions (T023, T024) both depend only on T022 and touch the same file
  sequentially; US3's and US4's backend work (T029-T031, T037-T039) can be staffed in parallel by
  different team members once Foundational is done, since both only read `Review` rows Foundational
  already defines — neither depends on US1's or US2's endpoints existing
- T042-T045 (Polish) marked [P] can run in parallel once all four stories are complete

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test POST /api/feedback/products/{id}/review/ (rating+comment) in backend/tests/feedback/test_customer_review_submit.py"
Task: "Contract test POST .../review/ (rating only) in backend/tests/feedback/test_customer_review_submit.py"
Task: "Contract test POST .../review/ rejected without DELIVERED purchase in backend/tests/feedback/test_customer_review_eligibility.py"
Task: "Contract test repeat POST .../review/ upserts in backend/tests/feedback/test_customer_review_upsert.py"
Task: "Contract test DELETE .../review/ in backend/tests/feedback/test_customer_review_delete.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 independently
5. Demo: a Customer can leave, update, and delete a review on a product they received

### Incremental Delivery

1. Setup + Foundational → `feedback` app, `Review` schema, eligibility check ready
2. US1 → validate (quickstart Scenario 1) → demo (Customer feedback MVP)
3. US2 → validate (quickstart Scenario 2) → demo (shoppers see reviews + rating)
4. US3 → validate (quickstart Scenario 3) → demo (Vendor feedback visibility)
5. US4 → validate (quickstart Scenario 4) → demo (Administrator moderation)
6. Phase 7 polish (also exercises quickstart Scenario 5) → final review against Constitution
   before considering the feature done

### Constitution alignment (Principle V: Spec-Driven, Staged Delivery)

Per the Constitution, implementation MUST proceed in reviewable chunks — **one phase at a time**,
each run for real (migrations applied, endpoints exercised via the DRF browsable API or the actual
Next.js dev server) and reviewed before starting the next. Do not run `/speckit-implement` to
generate all 45 tasks unattended; implement and check off one phase (ideally one user story) at a
time.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability back to spec.md
- Each user story is independently completable and testable per its Independent Test statement
- Verify contract tests fail before implementing the view/serializer that makes them pass
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
- Total: 45 tasks (T001-T045) across Setup (3), Foundational (4), US1 (10), US2 (8), US3 (8),
  US4 (8), Polish (4)

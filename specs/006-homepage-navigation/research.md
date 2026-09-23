# Phase 0 Research: Role-Aware Homepage & Shared Navigation

## 1. How to get "N most recent" items from existing list endpoints

**Decision**: Add a small, shared `apps/core/pagination.py` pagination class with
`page_size_query_param = "page_size"` and a capped `max_page_size` (e.g. 24), applied to the four
existing list views the homepage reads from (`CatalogProductListView`, `VendorOrderItemListView`,
`AdminOrderItemListView`, `AdminShopListView`). Homepage widgets request `?page_size=8` (products)
or `?page_size=5` (orders) explicitly.

**Rationale**: Every relevant queryset is already ordered newest-first (`-created_at` for
products/shops, `-order__placed_at` for order items) and already server-side permission/ownership
filtered — confirmed by reading `backend/apps/catalog/views.py`, `backend/apps/vendors/views.py`,
`backend/apps/orders/views.py`. The only gap is that DRF's global `PageNumberPagination` (
`backend/config/settings.py`, `PAGE_SIZE = 20`, no `PAGE_SIZE_QUERY_PARAM` set) has no way to
request fewer than 20 items. Without this change, the homepage would have to fetch the full
default page (20 rows) and slice to 5–8 client-side on every load, wasting bandwidth/DB work for
a page every visitor hits. A shared, capped, opt-in query param is a minimal, constitution-
consistent change (constitution's "Resource Utilization" NFR: paginate list endpoints, avoid
unnecessary over-fetching) that every existing caller of these four views can safely ignore
(behavior is byte-for-byte unchanged when `page_size` is omitted).

**Alternatives considered**:
- *Over-fetch default page (20) and slice client-side*: zero backend changes, but wastes ~2.5x-4x
  the needed rows on every homepage view for four different widgets, and would need to be redone
  if `PAGE_SIZE` ever changes. Rejected as wasteful for a page every visitor loads.
- *Four new dedicated "summary" endpoints (e.g. `/api/catalog/products/featured`)*: contradicts
  the spec's explicit preference (Assumptions) for reusing existing data exposure over new
  endpoints, and is more surface area than a single shared pagination change.
- *A dedicated homepage-aggregate endpoint (single call returns everything for the current
  user's role)*: appealing for request count, but couples an otherwise-presentation-only feature
  to new backend aggregation logic per role, harder to test in isolation per user story, and not
  necessary at this MVP scale (spec Scale/Scope: learning-project scale, at most 2 requests per
  role is fine). Rejected as premature — can be revisited later if the homepage grows.

## 2. Vendor shop status: reuse `useAuth().user.shops` vs. a fresh fetch

**Decision**: Read the Vendor's shop status for the homepage directly from `useAuth().user.shops`
(populated by the existing `/api/auth/me` call, `ShopBriefSerializer`: `id, name, status`) — no
new request. Only if the homepage needs to show a rejection reason does it fall back to the
existing `GET /api/vendor/shops` (full `ShopSerializer`, includes `status_reason`).

**Rationale**: `user.shops` is already loaded on every session restore
(`frontend/src/lib/auth-context.tsx`) before any page renders, so using it costs zero extra
requests and matches how `frontend/src/app/account/page.tsx` already displays shop info. Spec's
User Story 4 only requires showing status (approved/pending/rejected) plus a link to the account
page for resubmission — not the reason text — so the zero-fetch path covers the required scope;
the fallback stays available for the account page's existing use of `status_reason`, unchanged.

**Alternatives considered**: Always calling `GET /api/vendor/shops` for consistency — rejected as
an unnecessary duplicate request when `user.shops` already has everything User Story 4 needs.

## 3. Admin "shops pending approval" count without fetching every pending shop

**Decision**: Call the existing `GET /api/admin/shops?status=PENDING&page_size=1` and read the
response's DRF pagination envelope `count` field (exact count of the full filtered queryset, not
just the returned page) rather than fetching all pending shops and counting client-side.

**Rationale**: `AdminShopListView` already supports `?status=` filtering and, once the Phase-1
pagination class from research.md §1 is applied, returns `{count, next, previous, results}` —
`count` is free and exact regardless of `page_size`. `page_size=1` (or any small size) minimizes
payload while the count itself is unaffected. This satisfies FR-006/User Story 5 without a new
"count" endpoint.

**Alternatives considered**: A dedicated `/api/admin/shops/pending-count` endpoint — rejected,
redundant with data the paginated list endpoint already returns for free.

## 4. Fixed widget sizes

**Decision**: Homepage shows up to 8 products (guest/customer) and up to 5 recent orders
(vendor/admin), per spec's Assumptions section ("a small, bounded set").

**Rationale**: Matches the spec's documented defaults; keeps each homepage request small and the
layout predictable without introducing a user-configurable setting this MVP doesn't need.

**Alternatives considered**: None — this was already settled in spec.md's Assumptions and is not
re-litigated here.

## 5. Nav bar placement and role-link sets

**Decision**: A single `frontend/src/components/nav.tsx` client component rendered once in
`frontend/src/app/layout.tsx` above `{children}`, inside the existing `<AuthProvider>`. Link sets:

| Visitor | Links |
|---|---|
| Guest | Home, Products, Login, Register |
| Customer | Home, Products, Cart, Orders, Account, Logout |
| Vendor | Home, My Products, Vendor Orders, Account, Logout |
| Administrator | Home, Shop Approvals, Order Oversight, Account, Logout |

**Rationale**: Reuses `useAuth()`'s existing `user`/`role`/`logout`, mirrors each role's existing
top-level pages found during exploration (`frontend/src/app/products`, `cart`, `orders`,
`vendor/products`, `vendor/orders`, `admin/shops`, `admin/orders`, `account`) — no new pages are
implied by the nav itself, it only links to what already exists. Placing it in `layout.tsx` (not
per-page) satisfies FR-007 (present on every page) with one implementation, not one per route.

**Alternatives considered**: A `middleware.ts`-driven route guard/redirect system — rejected; out
of scope per the plan-mode decision to keep this a unified content-switching homepage, not a
hard-redirect system, and the spec's edge cases already require server-side enforcement to remain
authoritative regardless of what the nav shows.

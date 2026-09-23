# Phase 1 Data Model: Role-Aware Homepage & Shared Navigation

This feature introduces **no new database entities** — it is a read-only presentation layer over
existing data. No migration is required.

## Entities read (existing, unchanged)

| Entity | Source app | Fields used by this feature |
|---|---|---|
| `User` | `apps.accounts` | `role`, `is_email_verified` (via `useAuth().user`) |
| `Shop` | `apps.vendors` | `id`, `name`, `status` (`PENDING`/`APPROVED`/`REJECTED`) via `user.shops` (brief) or `GET /api/vendor/shops` (full, adds `status_reason`, `created_at`) |
| `Product` | `apps.catalog` | `id`, `name`, `price`, `image` (whatever `CatalogProductListSerializer` already exposes) via `GET /api/catalog/products` |
| `Order` / `OrderItem` | `apps.orders` | Whatever `VendorOrderItem`/`AdminOrderItem` TypeScript types already expose (id, product, status, `order.placed_at`) via `GET /api/vendor/order-items` / `GET /api/admin/order-items` |

## New/changed response shape

Only one backend-visible change: the four list endpoints below gain an **optional** `page_size`
query parameter (default behavior unchanged when omitted). No serializer fields change.

| Endpoint | New param | Existing response shape (unchanged) |
|---|---|---|
| `GET /api/catalog/products` | `page_size` (opt-in) | `{count, next, previous, results: CatalogProduct[]}` |
| `GET /api/vendor/order-items` | `page_size` (opt-in) | `{count, next, previous, results: VendorOrderItem[]}` |
| `GET /api/admin/order-items` | `page_size` (opt-in) | `{count, next, previous, results: AdminOrderItem[]}` |
| `GET /api/admin/shops` | `page_size` (opt-in) | `{count, next, previous, results: AdminShop[]}` (currently under-typed on the frontend as `{results: AdminShop[]}` — widened, not changed, to include `count`) |

## Frontend-only types (no backend equivalent)

These exist purely to shape what the new `Nav` and homepage components render; they are derived
from `useAuth().user`, not fetched separately.

- **NavLinkSet**: the list of `{label, href}` pairs shown for a given visitor (guest / CUSTOMER /
  VENDOR / ADMINISTRATOR), as enumerated in research.md §5. Computed in `nav.tsx`, not persisted.
- **HomepageSection state**: per-widget `{status: "loading" | "loaded" | "empty" | "error", data}`
  used to satisfy FR-011/FR-012 (explicit loading/empty/error states per section). Local component
  state only, not a shared type.

# Contract: Homepage & Nav Data Sources

No new endpoints. This documents the one backend-visible change and the exact calls the homepage
and nav make against existing endpoints.

## Backend change: opt-in `page_size` on four existing list views

Applies to `CatalogProductListView`, `VendorOrderItemListView`, `AdminOrderItemListView`,
`AdminShopListView` via a new shared class:

```python
# backend/apps/core/pagination.py
class LimitedPageNumberPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 24
```

- Omitting `page_size` → identical behavior to today (`PAGE_SIZE = 20` default, same response
  shape `{count, next, previous, results}`).
- `?page_size=N` (1 ≤ N ≤ 24) → returns up to N results; `count`/`next`/`previous` still reflect
  the full filtered queryset.
- No change to any view's `permission_classes`, `get_queryset()` filtering, ordering, or
  serializer.

## Calls the homepage makes, by visitor type

| Visitor | Call(s) | Purpose |
|---|---|---|
| Guest | `GET /api/catalog/products?page_size=8` | Product highlights |
| Customer | `GET /api/catalog/products?page_size=8` | Featured/recent products (cart/orders links use existing `user` state + static hrefs, no extra call) |
| Vendor | `GET /api/vendor/order-items?page_size=5` | Recent orders for their shop. Shop status comes from already-loaded `useAuth().user.shops` — no extra call unless a rejection reason must be shown, in which case `GET /api/vendor/shops` |
| Administrator | `GET /api/admin/shops?status=PENDING&page_size=1` (read `.count`) and `GET /api/admin/order-items?page_size=5` | Pending-shop count; recent platform orders |

## Calls the nav bar makes

None beyond what `useAuth()` already loads (`user`, `user.role`) on session restore. The nav never
issues its own network requests.

## Auth/permission behavior (unchanged — verify, do not modify)

- `GET /api/catalog/products` — `AllowAny`, filters to `is_published=True, shop__status=APPROVED`.
- `GET /api/vendor/order-items` — `IsVendor`, filters `product__shop__owner=request.user`.
- `GET /api/admin/order-items` — `IsAdministrator`, unfiltered (admin sees all).
- `GET /api/admin/shops` — `IsAdministrator`, optional `?status=` filter.
- A logged-out or wrong-role caller hitting the Vendor/Admin endpoints directly continues to
  receive the existing 401/403 behavior — this feature does not touch that enforcement, only adds
  an optional pagination knob.

## Login/Register redirect change

`frontend/src/app/login/page.tsx` and `frontend/src/app/register/page.tsx`: on success,
`router.push("/account")` → `router.push("/")`. No backend contract change.

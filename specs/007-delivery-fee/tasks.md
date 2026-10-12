# Tasks: Mandatory Delivery with Distance-Based Fee

**Feature**: `007-delivery-fee` | **Spec**: [spec.md](spec.md)

**Note**: The user asked to implement straight from the spec and the approved plan, so this file records the tasks as built, in the phases they were delivered and verified. There is no separate plan.md.

## Phase A: Backend core (US1, US2, US3)

- [x] T001 Add delivery pricing fields to `PlatformSettings` (base, per-km, minimum, max distance, road factor) with validators. Files: `backend/apps/finance/models.py`, migration `finance/0003`.
- [x] T002 Add `latitude`, `longitude`, `location_address` and `has_location` to `Shop`. Files: `backend/apps/vendors/models.py`, migration `vendors/0005`.
- [x] T003 Add the delivery pin and `delivery_fee` to `Order`, plus `items_subtotal`. `Order.total` now includes delivery. Add a new `OrderDelivery` leg model. Files: `backend/apps/orders/models.py`, migration `orders/0005`.
- [x] T004 Write the pricing service: `haversine_km`, `leg_fee`, `quote_delivery` and `DeliveryError`. File: `backend/apps/delivery/pricing.py`.
- [x] T005 Write pricing unit tests. File: `backend/tests/delivery/test_pricing.py`.

## Phase B: Backend API (US1–US4)

- [x] T006 `DeliveryPinSerializer`: the checkout `shipping` now requires `latitude`/`longitude`. File: `backend/apps/orders/serializers.py`.
- [x] T007 Change `place_order()` so it recomputes the legs server-side and charges items + delivery. It records the legs and the order's `delivery_fee`, and turns `DeliveryError` into a `CheckoutError` with a code. File: `backend/apps/orders/services.py`.
- [x] T008 Add `POST /api/checkout/delivery-quote` (customer only). Files: `backend/apps/orders/views.py`, `urls.py`.
- [x] T009 Order serializers expose `items_subtotal`, `delivery_fee`, `total`, `deliveries` and the shipping pin (customer, vendor and admin views).
- [x] T010 Shop location endpoints:
  - `PUT /api/vendor/shops/:id/location` (owner)
  - `PUT /api/admin/shops/:id/location` (admin)

  Owner profile and admin shop detail now include the location. The public shop serializer is unchanged.
- [x] T011 Admin settings `PATCH` accepts any subset of the commission and delivery pricing fields (`update_platform_settings`).
- [x] T012 The finance summary gains `delivery_revenue`. Gross sales and shop balances still exclude delivery.
- [x] T013 Rider deliveries include the shop's pickup address and coordinates, and the dropoff coordinates.
- [x] T014 Admin customer `total_spent` and recent-order totals include delivery fees.
- [x] T015 Tests:
  - New: `tests/orders/test_checkout_delivery.py` and `tests/finance/test_delivery_settings_and_revenue.py`.
  - Updated: the existing `SHIPPING` fixtures, `ShopFactory` coordinates, and total assertions.

## Phase C: Frontend checkout (US1)

- [x] T016 Add `leaflet` with OpenStreetMap tiles (no API key).
- [x] T017 API client types: `ShippingAddress`, `LatLng`, `DeliveryQuote`, `OrderTotals`, `getDeliveryQuote`, shop location calls, and delivery pricing. File: `frontend/src/lib/api-client.ts`.
- [x] T018 `LocationPicker` (tap or drag the pin, "Use my location") and geo helpers. Files: `frontend/src/components/location-picker.tsx`, `frontend/src/lib/geo.ts`.
- [x] T019 Checkout page: the pin is required, a live debounced quote shows a per-shop summary, and submit is disabled until a valid quote exists. File: `frontend/src/app/checkout/page.tsx`.
- [x] T020 `DeliverySummary` component plus tests. Geo helper tests.

## Phase D: Frontend other pages (US2–US4)

- [x] T021 Customer order page: fee breakdown and delivery-pin link. File: `frontend/src/app/orders/[id]/page.tsx`.
- [x] T022 Admin order page: items, per-shop delivery, fee, total and pin link.
- [x] T023 Rider deliveries: "Open pickup in maps" and "Open drop-off in maps" links.
- [x] T024 Vendor account: `ShopLocationEditor`, with a warning until a location is set. File: `frontend/src/app/account/page.tsx`.
- [x] T025 Admin shop detail: pickup location editor.
- [x] T026 Admin finance: "Delivery fees collected" stat and the delivery pricing form.
- [x] T027 Cart: shows the items total with a note that delivery is added at checkout.

## Verification

- Backend: full `pytest` suite green.
- Frontend: `tsc`, `eslint`, `vitest` and `next build` all green.
- Migrations applied to the dev database.
- End-to-end API run on the dev database (rolled back) covered:
  - The quote is blocked until shops set locations.
  - Vendor and admin location set.
  - Two-leg quote: 7.33 km → TZS 6,800 and 2.72 km → TZS 3,800.
  - Checkout charge equals the quote; a client-sent fee is ignored.
  - Delivery revenue and admin order totals.
- Browser walkthrough on dev (2026-10-12), using temporary test accounts that were deleted afterwards:
  - The vendor set a pin; the warning appeared before and cleared after.
  - Checkout was blocked until the admin set the second shop's location.
  - Live quote: Items TSh 15,000 + 6,800 (7.3 km) + 3,800 (2.8 km) = 25,600.
  - The order page showed the breakdown and pin link.
  - Admin order: delivery TSh 10,600 marked as mall revenue; commission and shop earnings only on items.
  - Admin finance: "Delivery fees collected" and the pricing form.
  - Rider card: pickup and drop-off maps links.
  - No console errors.

## Rollout

Existing production shops have no location. After deploying, admins or vendors must set every active shop's location before its products can be checked out again.

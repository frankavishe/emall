# Feature Specification: Mandatory Delivery with Distance-Based Fee

**Feature Branch**: `007-delivery-fee`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Mandatory delivery with distance-based fee. mangimall is an online-only mall, so every order must be delivered (no pickup). At checkout the customer types a delivery address AND confirms the exact location on a map, either by dropping/dragging a pin or by pressing 'Use my location' (GPS); a pin location is required to place the order. The delivery fee is calculated per shop in the cart: for each shop leg, fee = max(min_fee, base_fee + per_km_fee × straight-line distance × road_factor), rounded up to the nearest TZS 100; distance is measured from the shop's saved location to the customer's pin. Shops must set their own location (map pin + address) in vendor shop settings; admins can also edit shop locations. Products from a shop with no location cannot be checked out (clear error), and destinations beyond the admin-set maximum delivery radius are rejected. Admin edits pricing (base fee, per-km fee, minimum fee, max distance km, road factor) in finance settings. The customer sees a live quote on checkout (items subtotal, delivery fee per shop with km, total) before paying; the server always recomputes the fee and never trusts the client. The total charged = items subtotal + delivery fee. The mall keeps the delivery fee as platform revenue (not part of vendor earnings or commission); admin finance shows delivery revenue. Order pages (customer, admin) show the delivery fee line; riders see dropoff and shop pickup coordinates with an 'open in maps' link. Uses free OpenStreetMap/Leaflet maps, with no paid geocoding API."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer pins a delivery location and pays a distance-based delivery fee (Priority: P1)

A Customer with items in their cart goes to checkout. Because mangimall is an online-only mall, delivery is the only option. The Customer types their delivery address, then confirms the exact spot on a map. They can either press "Use my location" so the device's GPS places the pin, or drop and drag the pin themselves. As soon as a pin is set, the checkout page shows a quote with:
- the items subtotal
- a delivery fee for each shop whose products are in the cart, with that shop's distance
- the grand total

The Customer places the order and is charged the items subtotal plus the delivery fee.

**Why this priority**: This is the core of the feature. Without it, orders carry no delivery location precise enough for a rider, and the mall collects no delivery revenue.

**Independent Test**:
1. Give two shops saved locations.
2. As a Customer, add products from both shops to the cart.
3. At checkout, set a pin and confirm the quote shows two delivery legs with distances and fees.
4. Place the order and confirm the charged amount equals the items subtotal plus the sum of both fees.

**Acceptance Scenarios**:

1. **Given** a Customer at checkout with no pin set, **When** they try to place the order, **Then** they cannot, and are told to set their delivery location on the map.
2. **Given** a Customer at checkout, **When** they press "Use my location" and grant permission, **Then** the pin moves to their current position and the delivery quote updates.
3. **Given** a Customer at checkout, **When** they press "Use my location" and deny permission (or GPS is unavailable), **Then** they see a clear message and can still place the pin by hand.
4. **Given** a cart with products from two shops and a pin set, **When** the quote is shown, **Then** it lists each shop with its distance and fee, and the total equals the items subtotal plus the sum of the shop fees.
5. **Given** a Customer who moves the pin, **When** the pin settles, **Then** the quote recalculates for the new location.
6. **Given** a Customer places an order, **When** checkout completes, **Then** the amount charged and the order total both equal the items subtotal plus the delivery fee computed by the system at that moment. Any fee value the client sends is ignored.
7. **Given** a pin farther from a shop than the maximum delivery distance, **When** the quote is requested or the order is placed, **Then** the order is rejected with a message that the location is outside the delivery area for that shop.

---

### User Story 2 - Vendor sets their shop's location (Priority: P1)

A Vendor opens their shop settings and sets the shop's location. They type a pickup address and confirm the spot on the same kind of map (pin or "Use my location"). Until a shop has a location, its products cannot be checked out. The Vendor is warned about this prominently.

**Why this priority**: Delivery fees are measured from each shop. Without shop locations, no order can be priced, so this is required alongside User Story 1.

**Independent Test**:
1. As a Vendor whose shop has no location, see the warning.
2. Set a location and confirm it is saved and the warning disappears.
3. As a Customer, confirm that checkout of that shop's products now succeeds where it previously failed.

**Acceptance Scenarios**:

1. **Given** a Vendor whose shop has no location, **When** they open their shop settings, **Then** they see a warning that customers cannot check out their products until a location is set.
2. **Given** a Vendor, **When** they set a pin and address and save, **Then** the shop's location is stored, and later delivery quotes for its products use it.
3. **Given** a Customer whose cart contains a product from a shop without a location, **When** they request a quote or try to place the order, **Then** the order is blocked with a message naming that shop.
4. **Given** an Administrator viewing a shop's detail, **When** they set or correct the shop's location, **Then** the change is saved and used for later quotes.

---

### User Story 3 - Administrator configures delivery pricing and sees delivery revenue (Priority: P2)

An Administrator opens the finance settings and adjusts these delivery pricing values:
- base fee
- per-kilometre fee
- minimum fee
- maximum delivery distance
- road factor, which turns straight-line distance into an approximate road distance

New quotes use the updated values immediately. The finance overview shows total delivery revenue collected. This revenue belongs to the mall and is separate from vendor earnings and commission.

**Why this priority**: Sensible defaults let the feature work without this story. Admin control and revenue visibility are still needed for the mall to run delivery as a business.

**Independent Test**:
1. As an Administrator, change the per-km fee.
2. Request a quote for the same cart and pin as before, and confirm the fee changed accordingly.
3. Place an order and confirm delivery revenue in the finance overview increases by that order's delivery fee, while vendor earnings are unchanged.

**Acceptance Scenarios**:

1. **Given** an Administrator, **When** they save new delivery pricing values, **Then** the next quote uses them.
2. **Given** an Administrator enters an invalid value (negative fee, zero or negative maximum distance, road factor below 1), **When** they save, **Then** the save is rejected with a field-level message.
3. **Given** orders with delivery fees, **When** the Administrator views the finance overview, **Then** total delivery revenue is shown, and the delivery fees are not counted in vendor earnings or commission.
4. **Given** a non-Administrator, **When** they try to read or change delivery pricing, **Then** the request is refused.

---

### User Story 4 - Delivery details shown after the order (Priority: P2)

After an order is placed:
- The Customer's order page shows the items subtotal, the delivery fee and the total.
- The Administrator's order detail shows the same, plus the delivery location.
- A Rider assigned to deliver an item sees both the shop's pickup location and the customer's dropoff location. Each has an "open in maps" link that opens a maps app or site at that exact spot.

**Why this priority**: This makes the captured location and fee useful downstream. It depends on User Story 1 producing the data.

**Independent Test**:
1. Place an order with a pin.
2. Confirm the Customer and Administrator order views show the fee breakdown.
3. Assign a rider and confirm the rider's delivery view links to both the pickup and the dropoff location.

**Acceptance Scenarios**:

1. **Given** a placed order with a delivery fee, **When** the Customer views it, **Then** they see items subtotal, delivery fee and total, and the figures add up.
2. **Given** an assigned delivery, **When** the Rider views it, **Then** they see an "open in maps" link for the pickup (shop) location and for the dropoff (customer) location.
3. **Given** an order placed before this feature existed (no pin, no fee), **When** anyone views it, **Then** it displays correctly with a delivery fee of zero and no map link.

---

### Edge Cases

- **Cart changes after the quote**: The quote is advisory. At order placement the system recalculates using the current cart, the current shop locations and the current pricing. The Customer is charged that recalculated amount.
- **Several items from the same shop**: That shop is charged one delivery fee, not one fee per item.
- **Pin at exactly the shop's location (zero distance)**: The minimum fee applies.
- **Pin at exactly the maximum distance**: Accepted. Only distances beyond the maximum are rejected.
- **One shop in range, another out of range**: The whole order is rejected with a message naming the out-of-range shop. The Customer can remove that shop's items and retry.
- **Invalid coordinates (out of range, missing, non-numeric)**: Rejected with a field-level error.
- **Shop location removed or changed while a cart is open**: The next quote and the order placement use the current state.
- **GPS unavailable or slow**: The Customer is never blocked from placing the pin by hand. A GPS failure shows a message and does not stop the form from working.
- **Map tiles fail to load (poor connection)**: The page shows a message. The address fields stay usable, but the order still cannot be placed without a pin.
- **Payment declined**: As today, no order is created and nothing is charged, including the delivery fee.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every order MUST be a delivery order. There MUST be no pickup or collect-in-store option.
- **FR-002**: Checkout MUST require a typed delivery address (the existing address fields) **and** a delivery location as map coordinates. An order MUST NOT be accepted without valid coordinates.
- **FR-003**: Customers MUST be able to set the delivery location by placing or dragging a pin on a map, or by using their device's location ("Use my location").
- **FR-004**: Each Shop MUST be able to store a location (coordinates plus a pickup address). The shop's Vendor MUST be able to set and change it, and Administrators MUST be able to set and change it for any shop.
- **FR-005**: The system MUST calculate a separate delivery fee for each distinct shop with products in the order:
  - fee = max(minimum fee, base fee + per-km fee × distance × road factor)
  - The result is rounded **up** to the nearest TZS 100.
  - Distance is the straight-line (great-circle) distance in kilometres between the shop's location and the customer's delivery location.
- **FR-006**: The order's delivery fee MUST be the sum of the per-shop fees. The total charged MUST be the items subtotal plus the delivery fee.
- **FR-007**: The system MUST reject a quote or order when any shop in it has no saved location, with a message naming the shop.
- **FR-008**: The system MUST reject a quote or order when the distance from any shop to the delivery location exceeds the configured maximum delivery distance, with a message naming the shop.
- **FR-009**: Customers MUST be able to get a delivery quote for their current cart and a chosen location before placing the order. The quote shows:
  - the items subtotal
  - each shop's name, distance and fee
  - the total delivery fee
  - the grand total
- **FR-010**: At order placement, the system MUST recalculate the delivery fee itself from current data. It MUST NOT accept a fee or total supplied by the client.
- **FR-011**: The system MUST record, with each order:
  - the delivery coordinates
  - the total delivery fee
  - for each shop: the distance and the fee charged

  These values must not change if pricing settings or shop locations change later.
- **FR-012**: Administrators MUST be able to view and update the delivery pricing settings:
  - base fee
  - per-km fee
  - minimum fee
  - maximum delivery distance in km
  - road factor

  Validation rules:
  - Fees MUST be ≥ 0.
  - Maximum distance MUST be > 0.
  - Road factor MUST be ≥ 1.
- **FR-013**: Only Administrators MAY read or change delivery pricing settings, and only a Shop's own Vendor or an Administrator MAY change that shop's location. These checks are enforced server-side.
- **FR-014**: Delivery fees MUST be treated as mall (platform) revenue. They MUST NOT be included in vendor earnings, commission calculations or payouts.
- **FR-015**: The Administrator finance overview MUST show total delivery revenue.
- **FR-016**: The Customer order view and the Administrator order view MUST show the items subtotal, the delivery fee and the total.
- **FR-017**: A Rider's delivery view MUST show the pickup (shop) and dropoff (customer) locations, each with a link that opens the location in a maps app or website.
- **FR-018**: Orders created before this feature MUST continue to display and function, treating the delivery fee as zero and the location as absent.
- **FR-019**: A Vendor whose shop has no location MUST see a warning that customers cannot check out the shop's products until it is set.
- **FR-020**: Maps MUST work without any paid mapping or geocoding service. The typed address is stored as entered, with no automatic lookup.

### Key Entities

- **Delivery Pricing Settings**: the mall-wide values used to calculate fees (base fee, per-km fee, minimum fee, maximum delivery distance, road factor). There is a single set, edited by Administrators.
- **Shop Location**: a shop's pickup coordinates and pickup address. It is optional until set, and checkout requires it.
- **Order delivery details**: the customer's delivery coordinates and the order's total delivery fee, stored alongside the existing typed address on the Order.
- **Order Delivery Leg**: one per shop in an order. It records the shop, the distance used and the fee charged, so the fee breakdown can be audited and shown later.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of new orders carry delivery coordinates and a recorded delivery fee. No order can be placed without them.
- **SC-002**: For every order, the amount charged equals the items subtotal plus the sum of the recorded per-shop fees, with no rounding discrepancy.
- **SC-003**: A Customer can set their delivery location and see an updated quote within 2 seconds of placing or moving the pin, on a typical mobile connection.
- **SC-004**: A Customer using "Use my location" can set their delivery location and place the order in under 3 minutes from opening checkout.
- **SC-005**: Delivery revenue in the finance overview equals the sum of delivery fees on all paid orders. Vendor earnings are identical to what they would be without the delivery fee.
- **SC-006**: A Rider can open both the pickup and dropoff locations in a maps app with a single tap each.
- **SC-007**: A change to delivery pricing takes effect on the very next quote, with no restart or redeploy.

## Assumptions

- **Default pricing values** until an Administrator changes them:
  - base fee: TZS 2,000
  - per-km fee: TZS 500
  - minimum fee: TZS 2,000
  - maximum delivery distance: 50 km
  - road factor: 1.30
- **Distance**: Straight-line distance multiplied by the road factor is an acceptable approximation of road distance. Real road routing is out of scope.
- **Fee per shop**: The fee is charged once per distinct shop in the order, matching how each shop's items travel as a separate pickup.
- **Existing shops**: Shops have no location at launch. They must set one before their products can be checked out. This is an accepted rollout step, not a defect.
- **Currency**: All amounts are in TZS, the existing store currency.
- **Payment**: The existing (mock) payment flow is reused unchanged, except that it is charged the new total.
- **Scope**: Delivery fees are not refunded or split when individual items are cancelled. Refund handling is out of scope for this feature.
- **Rider pay**: Riders are not paid from the delivery fee in this feature. Rider payouts are out of scope.
- **Map provider**: The map uses free, publicly available map tiles. Device location requires the Customer's browser permission and a secure (HTTPS) connection in production.

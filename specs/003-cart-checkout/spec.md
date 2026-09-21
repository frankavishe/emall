# Feature Specification: Shopping Cart & Checkout

**Feature Branch**: `003-cart-checkout`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Shopping cart and checkout flow: customers can add products from the catalog to a persistent cart, adjust quantities, remove items, and proceed through a checkout flow that captures shipping details and produces an order. Should build on the existing 001-accounts-auth (customer/vendor/admin roles) and 002-product-catalog (Product, Category, approval-gated vendor catalog) features already implemented in this repo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer builds and manages a persistent cart (Priority: P1)

A logged-in Customer browses the published catalog, adds products to their cart with a chosen
quantity, and later returns (even from a different device or after logging out and back in) to
find their cart exactly as they left it. They can increase or decrease the quantity of any line,
or remove a line entirely.

**Why this priority**: Without a working cart, there is nothing to check out — this is the
foundation every other story in this feature depends on, and it is independently useful/visible on
its own (a Customer can build a cart even before checkout exists).

**Independent Test**: Can be fully tested by logging in as a Customer, adding two different
published products to the cart with different quantities, logging out and back in (or hitting the
API fresh) and confirming the same cart contents are returned, then adjusting a quantity and
removing a line and confirming the cart reflects both changes.

**Acceptance Scenarios**:

1. **Given** a logged-in Customer viewing a published product, **When** they add it to their cart
   with quantity 2, **Then** the cart contains a line for that product with quantity 2 and a
   correct subtotal (unit price × quantity).
2. **Given** a Customer with items already in their cart, **When** they log out and log back in (or
   open the app on a different device), **Then** their cart still contains the same items and
   quantities.
3. **Given** a Customer's cart with a product at quantity 2, **When** they change the quantity to
   5, **Then** the cart line updates to quantity 5 and the cart total recalculates.
4. **Given** a Customer's cart with two product lines, **When** they remove one line, **Then** only
   that line is removed and the remaining line and cart total are unaffected.
5. **Given** a Customer attempts to add a quantity of a product greater than its currently available
   stock, **When** they submit the add-to-cart request, **Then** the system rejects the request
   with a clear message stating the maximum available quantity.

---

### User Story 2 - Customer completes checkout and places an order (Priority: P1)

A Customer with items in their cart proceeds to checkout, enters shipping details, confirms their
order, and — after a (mocked) payment step succeeds — receives a placed order with a confirmation
showing everything that was ordered, from which vendor(s), and at what price. Their cart is emptied
and each vendor's shop only needs to fulfill the line items that belong to it.

**Why this priority**: This is the entire point of the feature — a cart with no way to convert it
into a real order delivers no business value. It depends on User Story 1 (a cart must exist) but is
the story that actually produces the Order the rest of the system (fulfillment, payments) builds on.

**Independent Test**: Can be fully tested by logging in as a Customer with a non-empty cart,
submitting shipping details and confirming checkout, and verifying an Order is created with the
correct line items, prices, shipping details, and a per-line-item status for each vendor's
products, that the corresponding products' stock quantities were decremented by the ordered
amounts, and that the Customer's cart is now empty.

**Acceptance Scenarios**:

1. **Given** a Customer with a non-empty cart containing products from a single vendor, **When**
   they submit valid shipping details and confirm checkout, **Then** an Order is created with one
   line item per cart line (capturing product, quantity, and price at time of purchase), the
   ordered products' stock is decremented accordingly, the cart is emptied, and the Customer sees
   an order confirmation.
2. **Given** a Customer with a cart containing products from two different vendors' shops, **When**
   they complete checkout, **Then** a single Order is created containing line items from both
   shops, each line item carrying its own fulfillment status so each vendor can manage only its own
   lines.
3. **Given** a Customer attempts to check out with an empty cart, **When** they submit the checkout
   request, **Then** the system rejects it with a clear message and no Order is created.
4. **Given** a Customer's cart contains a line whose quantity now exceeds the product's current
   available stock (e.g. stock dropped after it was added to the cart), **When** they attempt
   checkout, **Then** the system blocks checkout, reports exactly which line(s) are the problem, and
   creates no Order and decrements no stock.
5. **Given** a Customer completes checkout, **When** the (mocked) payment step fails, **Then** no
   Order is created, no stock is decremented, and the Customer's cart remains unchanged so they can
   retry.
6. **Given** a Customer omits a required shipping field (e.g. address or postal code), **When**
   they submit checkout, **Then** the system rejects the request with a field-level validation
   message and does not create an Order.

---

### User Story 3 - Cart reflects live catalog changes (Priority: P2)

While a product sits in a Customer's cart, its price, availability, or publish status may change
(a vendor edits the price, runs out of stock, or unpublishes the product). The Customer's cart
clearly reflects the current, real state of each line rather than stale data, both while viewing
the cart and at checkout.

**Why this priority**: Prevents Customers from being charged a stale price or ordering something no
longer available, and prevents vendors from being forced to fulfill stock they no longer have. It
depends on Stories 1 and 2 already existing but is a correctness/trust safeguard on top of them
rather than new core functionality.

**Independent Test**: Can be fully tested by adding a product to a cart, having a vendor change its
price/stock/publish status directly via the catalog feature, then viewing the cart and attempting
checkout — confirming the cart displays current data and checkout enforces it.

**Acceptance Scenarios**:

1. **Given** a product in a Customer's cart whose price has changed since it was added, **When**
   the Customer views their cart, **Then** the cart shows the product's current price and
   recalculated subtotal/total, not the price at the time it was added.
2. **Given** a product in a Customer's cart that a vendor has since unpublished, **When** the
   Customer views their cart, **Then** that line is clearly flagged as unavailable and is excluded
   from the checkout total until removed.
3. **Given** a cart line flagged unavailable (unpublished or out of stock), **When** the Customer
   attempts checkout, **Then** checkout is blocked until the Customer removes or adjusts that line.

---

### User Story 4 - Customer reviews past orders (Priority: P3)

After placing one or more orders, a Customer can see a list of their past orders and open any one
of them to review exactly what was ordered, its shipping details, and the current per-line-item
status.

**Why this priority**: A nice-to-have completeness layer on top of checkout (Story 2 already
produces the order and a one-time confirmation) — valuable for trust and support, but the feature
is fully usable end-to-end without it.

**Independent Test**: Can be fully tested by placing two separate orders as the same Customer, then
requesting the Customer's order list and confirming both appear with correct summaries, and opening
one to confirm its full detail matches what was ordered.

**Acceptance Scenarios**:

1. **Given** a Customer who has placed two orders, **When** they view their order history,
   **Then** both orders appear, most recent first, each with date, total, and overall status.
2. **Given** a Customer opens one of their past orders, **When** the detail loads, **Then** it
   shows every line item (product, quantity, price paid), shipping details, and each line's current
   fulfillment status.
3. **Given** a Customer attempts to view another Customer's order by guessing/adjusting an order
   identifier, **When** the request is made, **Then** the system denies access.

---

### Edge Cases

- What happens when a Customer adds the same product to their cart twice? The existing line's
  quantity increases rather than creating a duplicate line.
- What happens when two concurrent checkout attempts (from the same or different Customers) would
  together oversell a product's remaining stock? Only the requests that fit within available stock
  at commit time succeed; the rest are rejected as a stock conflict with no partial order created.
- What happens if a vendor's shop is later un-approved (Constitution Principle II) while one of its
  products is still sitting in a Customer's cart? The line behaves like an unpublished product
  (flagged unavailable, excluded from checkout) since an un-approved shop's listings are no longer
  eligible for new orders.
- What happens when a Customer's cart is empty and they open the cart page? They see an empty-cart
  state with no totals and no way to proceed to checkout.
- How does the system handle a checkout request for a cart that contains only unavailable lines?
  It is treated the same as an empty-cart checkout attempt — rejected with a clear message.
- What happens when a Customer removes the last item from their cart during checkout in another
  tab/device? The checkout re-validation (User Story 2, Scenario 4) catches the now-empty/changed
  cart and blocks the stale request.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a logged-in Customer to add a published product to their cart with
  a specified quantity of at least 1.
- **FR-002**: System MUST allow a Customer to view their own cart's contents: each line's product,
  quantity, current unit price, line subtotal, and an overall cart total.
- **FR-003**: System MUST allow a Customer to change the quantity of an existing cart line.
- **FR-004**: System MUST allow a Customer to remove a line from their cart entirely.
- **FR-005**: Adding a product already present in the cart MUST increase that line's quantity
  rather than create a second line for the same product.
- **FR-006**: Cart contents MUST persist server-side per Customer account, surviving logout/login
  and access from a different device or browser.
- **FR-007**: System MUST reject adding to cart, or updating a cart line's quantity to, a quantity
  greater than the product's current available stock, with a message stating the available amount.
- **FR-008**: System MUST re-validate every cart line at checkout time — product still published,
  its shop still approved, quantity within current stock — and block checkout with a specific
  reason per failing line if any check fails.
- **FR-009**: Checkout MUST require shipping details: recipient name, address line, city,
  region/state, postal code, country, and a contact phone number.
- **FR-010**: System MUST reject checkout if required shipping details are missing or invalid,
  identifying which field(s) failed.
- **FR-011**: System MUST reject checkout of an empty cart, or a cart whose only lines are flagged
  unavailable, with a clear message and no Order created.
- **FR-012**: On successful checkout, system MUST create a single Order capturing: the Customer,
  one line item per cart line (product, quantity, and unit price at the moment of purchase), the
  shipping details, an overall order status, and a placed-at timestamp.
- **FR-013**: A single Order MUST be able to contain line items belonging to more than one vendor's
  shop, and each line item MUST carry its own fulfillment status independent of the other lines in
  the same order (Constitution Principle VI).
- **FR-014**: System MUST decrement each ordered product's stock by the ordered quantity atomically
  with Order creation — if any part of checkout fails (stock conflict, payment failure, validation
  error), no Order MUST be created and no stock MUST be decremented (all-or-nothing).
- **FR-015**: System MUST process payment through a mocked payment step for this feature, recording
  only a payment method label, a status, and an opaque transaction reference — it MUST NOT store
  raw card numbers or CVV/CVC anywhere, including in the mock (Constitution Principle III).
- **FR-016**: If the mocked payment step reports failure, system MUST NOT create an Order or
  decrement any stock, and the Customer's cart MUST remain exactly as it was before the attempt.
- **FR-017**: On successful checkout, the Customer's cart MUST be emptied.
- **FR-018**: System MUST prevent a Customer from viewing, modifying, or checking out any cart other
  than their own.
- **FR-019**: System MUST allow a Customer to view an immediate confirmation of a just-placed order
  (line items, quantities, prices paid, shipping details, order status).
- **FR-020**: System MUST allow a Customer to list their own past orders (most recent first) and
  open any one to view its full detail.
- **FR-021**: System MUST prevent a Customer from viewing another Customer's order.
- **FR-022**: Only accounts with the Customer role MUST be able to hold a cart, add/modify cart
  lines, or place an order (Vendor and Administrator accounts are not Customers, per the existing
  single-role-per-account model from 001-accounts-auth).

### Key Entities

- **Cart**: Exactly one active cart per Customer account. Holds zero or more Cart Items and exposes
  a computed total based on their current line subtotals.
- **Cart Item**: A line within a Cart referencing a specific Product and a quantity. Price is not
  frozen on the line — it is always read live from the current Product at view/checkout time (see
  User Story 3).
- **Order**: The permanent record created by a successful checkout. Belongs to one Customer,
  carries the shipping details supplied at checkout, an overall status, a placed-at timestamp, and
  one or more Order Items. May span multiple vendors' shops.
- **Order Item**: A line within an Order, referencing the Product (and its shop, for vendor-side
  filtering), the quantity ordered, the unit price captured at the moment of purchase (independent
  of later Product price changes), and its own fulfillment status.
- **Payment Record**: A mocked payment attempt tied to an Order — method, status, and an opaque
  transaction reference only; never raw card data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Customer can add a product to their cart in a single action from a product's detail
  or listing view.
- **SC-002**: A Customer with a non-empty cart can complete checkout — enter shipping details,
  confirm, and reach an order confirmation — in under 3 minutes.
- **SC-003**: 100% of successful checkouts result in an Order whose stock decrements match its
  ordered quantities exactly, with zero orders left in a partially-created state after a failure.
- **SC-004**: 100% of a Customer's cart contents are preserved and correctly restored after
  logging out and back in, or switching devices.
- **SC-005**: 100% of checkout attempts against a stale cart (price changed, stock insufficient,
  product unpublished, or shop no longer approved) are blocked with a specific, actionable reason
  rather than silently succeeding or partially completing.
- **SC-006**: 100% of a Customer's own past orders are visible and viewable in their order history,
  and 0% of another Customer's orders are ever visible to them.

## Assumptions

- Only Customer-role accounts have a cart and place orders; Vendor and Administrator accounts do
  not, consistent with the single-role-per-account model already established in 001-accounts-auth.
- Carts require a logged-in Customer account (no anonymous/guest cart or guest checkout in this
  iteration) — a visitor must register or log in as a Customer before adding items to a cart.
- A checkout produces exactly one Order per attempt even when its line items span multiple
  vendors' shops; per-line-item fulfillment status (Constitution Principle VI) is what lets each
  vendor manage only the lines belonging to their own shop — the system does not split one checkout
  into several separate Orders.
- Product price at checkout is always the Product's current live price at the moment the Order is
  placed (not a price frozen when the item was first added to the cart); the price is only frozen
  onto the Order Item once the Order is actually created, per Constitution Principle IV/VI.
- Payment is fully mocked for this feature per Constitution Principle IV (a swappable payment
  service interface with one mock implementation) — no real payment gateway integration, and the
  mock is assumed to succeed unless a failure is deliberately simulated for testing.
- Shipping cost calculation, tax calculation, promotional/discount codes, saved/multiple shipping
  addresses, order cancellation or refunds, and vendor-side order fulfillment management (updating
  a line item's status, shipping/tracking) are out of scope for this feature and left for a future
  feature — this feature covers only Customer-side cart → checkout → Order creation → confirmation
  and read-only order history.
- Single currency throughout, matching the existing catalog Product price field — no multi-currency
  support.

# Feature Specification: Vendor Order Fulfillment

**Feature Branch**: `004-order-fulfillment`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Vendor order fulfillment: allow a Vendor to view the order line items (OrderItems) belonging to their own shop's products across all customer orders, and update each line item's status through a fulfillment lifecycle (e.g. PENDING -> PROCESSING -> SHIPPED -> DELIVERED, with CANCELLED as an alternate terminal state) independently of other vendors' line items on the same order. Customers can see the per-line-item status update reflected on their existing order detail page. Administrators can view fulfillment status across all orders/shops for oversight. Status transitions must be constrained to a valid forward sequence (no skipping backward, no arbitrary jumps) and scoped so a Vendor can only update line items for their own shop's products."

## Clarifications

### Session 2026-09-21

- Q: When a Vendor cancels an order line item (moving it to CANCELLED), should the system restore the cancelled quantity back to the product's available stock? → A: Yes — restore stock: cancelling a line item increments the product's stock_quantity by the cancelled quantity.
- Q: Who should be able to view a line item's fulfillment status history (the audit trail from FR-009)? → A: Administrator only — Vendors and Customers see just the current status, not the full change history.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendor views and fulfills their own order lines (Priority: P1) 🎯 MVP

A Vendor needs to see which of their shop's products have been ordered by Customers, and move
each ordered line through its fulfillment lifecycle (e.g. mark it as being processed, then
shipped, then delivered) as the real-world fulfillment work happens, independently of what other
vendors on the same multi-vendor order are doing.

**Why this priority**: This is the core gap the feature exists to close — today a Vendor has no
way to know an order was placed for their product or to act on it. Without this, the
cart→checkout→order flow (003-cart-checkout) is a dead end for vendors.

**Independent Test**: As a Vendor with an APPROVED shop, place a test order (as a Customer) that
includes one of that Vendor's products. Log in as the Vendor, confirm the line item appears in
their fulfillment queue, and advance its status through the lifecycle one step at a time,
confirming each transition succeeds and the status persists.

**Acceptance Scenarios**:

1. **Given** a Vendor with an APPROVED shop and a placed Order containing one of their products,
   **When** the Vendor opens their fulfillment view, **Then** they see that order line (product,
   quantity, current status, and enough order context to fulfill it — e.g. shipping address)
   listed among their pending fulfillment work.
2. **Given** an order line currently at PENDING, **When** the Vendor marks it PROCESSING, **Then**
   the line's status updates to PROCESSING and this is visible immediately in the Vendor's
   fulfillment view.
3. **Given** an order line at PROCESSING, **When** the Vendor marks it SHIPPED, **Then** the
   status updates to SHIPPED; **when** the Vendor later marks it DELIVERED, **Then** the status
   updates to DELIVERED and the line is treated as fulfillment-complete.
4. **Given** an Order containing line items from two different vendors' shops, **When** Vendor A
   updates their own line's status, **Then** Vendor B's line on the same order is unaffected and
   Vendor A never sees or can act on Vendor B's line.
5. **Given** a Vendor viewing their fulfillment queue, **When** they attempt to open or act on a
   line item belonging to another vendor's shop (e.g. via a guessed identifier), **Then** the
   system denies access and does not reveal that line's details.

---

### User Story 2 - Customer sees fulfillment progress on their order (Priority: P1)

A Customer who placed an order wants to know, per item, how far along fulfillment is — whether
it's still being processed, has shipped, or has been delivered — without contacting the vendor or
support.

**Why this priority**: Fulfillment status is only valuable to the business if the Customer who is
waiting on the order can actually see it; this is the other half of the same value loop as User
Story 1 and ships in the same increment so the feature is demonstrably useful end to end.

**Independent Test**: As a Customer with a placed order, open that order's existing detail page
and confirm each line item shows its current fulfillment status, and that the status changes when
a vendor advances it (re-checking the page after a vendor update shows the new status without any
other change to the order).

**Acceptance Scenarios**:

1. **Given** a Customer's placed order with lines from one or more vendors, **When** the Customer
   opens that order's detail page, **Then** each line item shows its own current fulfillment
   status.
2. **Given** a line item a vendor has just advanced from PROCESSING to SHIPPED, **When** the
   Customer reloads their order detail page, **Then** the line reflects SHIPPED.
3. **Given** an order spanning two vendors' shops where one line is DELIVERED and the other is
   still PENDING, **When** the Customer views the order, **Then** the two lines show their
   distinct, independent statuses (the order is not reduced to one single overall status that
   would hide this difference).

---

### User Story 3 - Administrator has fulfillment oversight (Priority: P3)

An Administrator wants to review fulfillment status across all orders and shops, to spot stalled
or cancelled fulfillment without needing to ask a specific vendor.

**Why this priority**: Valuable for operational oversight but not required for the core
Customer/Vendor fulfillment loop to function — the platform works correctly even if this view
ships slightly after User Stories 1 and 2.

**Independent Test**: As an Administrator, open the fulfillment oversight view and confirm order
line items across multiple vendors' shops are visible with their current statuses, without being
able to change any status from this view.

**Acceptance Scenarios**:

1. **Given** placed orders containing line items from multiple different vendors' shops, **When**
   an Administrator opens the oversight view, **Then** they see line items across all of those
   shops with each one's current fulfillment status and which shop/vendor it belongs to.
2. **Given** an Administrator viewing the oversight view, **When** they look for a way to directly
   change a line item's fulfillment status from that view, **Then** no such control exists —
   oversight is read-only; only the owning Vendor can advance their own line's status.
3. **Given** a line item that has passed through several statuses, **When** an Administrator
   inspects that line item, **Then** they can see its full status-change history (each status and
   when it was reached); a Vendor or Customer viewing the same line item sees only its current
   status, not this history.

---

### Edge Cases

- What happens when a Vendor attempts to move a line item backward (e.g. SHIPPED → PROCESSING) or
  skip a step (e.g. PENDING → DELIVERED)? The system MUST reject the transition and leave the
  status unchanged.
- What happens when a Vendor attempts to change the status of a line item that is already
  CANCELLED or DELIVERED (a terminal state)? The system MUST reject the change — terminal states
  are final.
- What happens when a Vendor cancels a line item mid-fulfillment (e.g. from PROCESSING)? The line
  moves to CANCELLED and cannot be advanced further; other line items on the same order are
  unaffected; the cancelled quantity is restored to the product's available stock (see FR-011).
- What happens when a Vendor's shop is later set to a non-APPROVED status while they still have
  in-flight order lines? Previously placed lines remain visible and their status history is
  preserved; whether the Vendor can still advance them further is governed by the same shop
  approval gate as the rest of the platform (Constitution Principle II) — a non-APPROVED shop
  cannot act on fulfillment any more than it can publish a catalog listing.
- What happens when an Order has multiple line items for the same vendor (same shop, different
  products)? Each line item has its own independent status; the Vendor sees and updates each one
  separately.
- How does a Customer know an order is fully fulfilled? When every line item on the order reaches
  a terminal state (DELIVERED or CANCELLED), the order as a whole is considered fulfillment-
  complete; the Customer's order view reflects this by showing every line at a terminal status
  (no separate order-level rollup status is introduced by this feature).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a Vendor to view a list of order line items whose product belongs
  to one of that Vendor's own shops, across all Customer orders, independent of which other
  vendors' line items appear on the same order.
- **FR-002**: Each order line item MUST carry a fulfillment status with the ordered values
  PENDING → PROCESSING → SHIPPED → DELIVERED, plus CANCELLED as an alternate terminal state
  reachable from PENDING or PROCESSING.
- **FR-003**: System MUST allow the owning Vendor to advance a line item's status only to the
  single next status in the forward sequence, or to CANCELLED from PENDING or PROCESSING; any
  other requested transition (backward, skipped, or from a terminal state) MUST be rejected
  without changing the stored status.
- **FR-004**: System MUST reject any attempt by a Vendor to view or change the status of an order
  line item whose product does not belong to one of that Vendor's own shops, and MUST NOT reveal
  that line item's details in the process of rejecting the attempt.
- **FR-005**: System MUST allow a Customer to view the current fulfillment status of every line
  item on their own placed orders, shown per line item (not collapsed into one order-wide status),
  on the order detail view already delivered by 003-cart-checkout.
- **FR-006**: System MUST NOT allow a Customer to change a line item's fulfillment status.
- **FR-007**: System MUST allow an Administrator to view the fulfillment status of order line
  items across all vendors' shops, including which shop/vendor each line belongs to.
- **FR-008**: System MUST NOT allow an Administrator to change a line item's fulfillment status
  through the oversight view (oversight is read-only; only the owning Vendor advances their own
  lines).
- **FR-009**: System MUST record, for each order line item, a history of its fulfillment status
  changes (at minimum: the status it moved to and when), so a stalled or disputed line can be
  investigated after the fact. This history MUST be visible only to Administrators — Vendors and
  Customers see only the line item's current status, not its full change history.
- **FR-010**: A Vendor's ability to update fulfillment status on their line items MUST be subject
  to the same shop-approval gate as the rest of the platform (Constitution Principle II) — a
  Vendor whose shop is not APPROVED MUST NOT be able to advance fulfillment status.
- **FR-011**: When a line item transitions to CANCELLED, the system MUST restore (increment) the
  product's available stock by the cancelled line item's quantity, so cancelled inventory becomes
  sellable again.

### Key Entities

- **Order Line Item (existing entity, extended)**: A single product/quantity/price line within a
  Customer's placed order, already scoped to one vendor's shop via its product. This feature adds
  a richer fulfillment status (beyond the current single "placed" state) and a change history to
  this entity; it does not change what an order line item represents. Transitioning a line item to
  CANCELLED also restores its quantity to the related product's available stock (FR-011).
- **Fulfillment Status History**: An ordered record of the statuses an order line item has passed
  through and when each change occurred, used for oversight and dispute resolution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Vendor can find and correctly identify every order line item awaiting their action
  within a few seconds of opening their fulfillment view, with no line belonging to another
  vendor's shop appearing in that view.
- **SC-002**: 100% of attempted invalid status transitions (backward, skipped, or from a terminal
  state) are rejected, and the line's stored status never changes as a result of a rejected
  attempt.
- **SC-003**: A Customer can see an up-to-date fulfillment status for every item on their order,
  with no more than one page reload needed to see a Vendor's most recent update.
- **SC-004**: On a multi-vendor order, each vendor's fulfillment actions are fully independent —
  one vendor advancing or cancelling their line item never changes another vendor's line item on
  the same order.
- **SC-005**: An Administrator can view fulfillment status across every shop's orders from a
  single view without needing to contact any vendor individually.
- **SC-006**: 100% of cancelled line items result in the product's available stock being increased
  by exactly the cancelled quantity, with no double-counting when multiple lines for the same
  product are cancelled independently.

## Assumptions

- The fulfillment lifecycle is PENDING → PROCESSING → SHIPPED → DELIVERED, with CANCELLED
  reachable as an alternate terminal state from PENDING or PROCESSING (not from SHIPPED, since a
  shipment already in transit is a real-world return/refund scenario, out of scope for this
  feature per Assumptions below).
- Only the four in-sequence statuses plus CANCELLED are in scope; there is no "returned" or
  "refunded" status in this feature — returns/refunds are a separate future feature.
- This feature extends the existing per-line-item `OrderItem` concept and its existing
  Customer-facing order detail page (both delivered by 003-cart-checkout) rather than introducing
  a new order-line entity or a new Customer-facing page.
- No notifications (email/SMS) are sent on status change in this feature; the Customer discovers
  the new status by viewing their order detail page. Notification delivery is a separate future
  feature.
- A Vendor cancelling their own line item does not automatically affect payment/refund records;
  payment/refund handling in response to a cancellation is out of scope for this feature.
- Fulfillment status changes are made one line item at a time by the Vendor; bulk/batch status
  updates across many line items at once are out of scope for this feature.
- The Vendor's fulfillment view is scoped to their own shop(s) only, reusing the existing Vendor
  role and shop-ownership model from 001-accounts-auth; no new roles are introduced.

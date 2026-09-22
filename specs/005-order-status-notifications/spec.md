# Feature Specification: Order Status Notifications

**Feature Branch**: `005-order-status-notifications`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Order status notifications: when a Vendor advances an OrderItem's fulfillment status (PROCESSING, SHIPPED, DELIVERED, CANCELLED), the Customer who placed the order is notified so they don't have to keep checking their order detail page manually. Builds on 004-order-fulfillment's existing OrderItemStatusEvent history and advance_order_item_status() service. Notification delivery channel (email) should reuse the existing swappable email-service pattern from apps/core/email.py (used for verification/reset emails in 001-accounts-auth) so the transport is mockable/swappable per Constitution Principle IV. Out of scope: SMS/push notifications, notification preferences/opt-out UI, real-time in-app notifications (websockets) — email only for this feature."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer is emailed when their item ships or is delivered (Priority: P1)

A Customer has placed an order containing one or more line items. A Vendor fulfilling one of those
line items marks it SHIPPED, and later marks it DELIVERED. The Customer receives an email each time,
telling them which item (and which order) the update is about, without needing to revisit the site.

**Why this priority**: "Where is my stuff?" is the single biggest source of unprompted
order-status checking and support inquiries. Shipped/delivered are the two updates a Customer is
most anxiously waiting for, so they deliver the most value for the least surface area.

**Independent Test**: Can be fully tested by having a Vendor advance an OrderItem to SHIPPED, then
to DELIVERED, via the existing fulfillment endpoint, and confirming one email is sent to the
Customer's registered address after each transition, each correctly identifying the order and item.

**Acceptance Scenarios**:

1. **Given** a Customer's order item is PROCESSING, **When** the owning Vendor advances it to
   SHIPPED, **Then** the Customer receives an email identifying the order and the specific item,
   stating it has shipped.
2. **Given** a Customer's order item is SHIPPED, **When** the owning Vendor advances it to
   DELIVERED, **Then** the Customer receives an email identifying the order and the specific item,
   stating it has been delivered.
3. **Given** an order with two line items fulfilled by two different Vendors, **When** each Vendor
   independently advances their own line item, **Then** the Customer receives one email per
   transition, each scoped to that Vendor's item only (not a combined summary of the whole order).

---

### User Story 2 - Customer is emailed when their item is cancelled (Priority: P2)

A Vendor is unable to fulfill a line item and cancels it. The Customer receives an email explaining
that this specific item was cancelled, so they know to look into it rather than assume it is still
coming.

**Why this priority**: Cancellation is lower-frequency than shipping/delivery but higher-stakes to
miss — a silently cancelled item is the scenario most likely to erode trust if the Customer isn't
told promptly. Ranked P2 because it is independently valuable but not required for US1's MVP to
stand on its own.

**Independent Test**: Can be fully tested by having a Vendor cancel an OrderItem via the existing
fulfillment endpoint and confirming the Customer receives an email identifying the order and item
and stating it was cancelled.

**Acceptance Scenarios**:

1. **Given** a Customer's order item is PROCESSING, **When** the owning Vendor cancels it, **Then**
   the Customer receives an email identifying the order and the specific item, stating it was
   cancelled.
2. **Given** a cancellation notification is sent, **Then** its wording does not state or imply any
   refund/payment outcome (payment handling for cancellations is out of scope per the
   004-order-fulfillment spec).

---

### User Story 3 - Customer is emailed when their item enters processing (Priority: P3)

A Vendor begins working on a line item and advances it to PROCESSING. The Customer receives an
email confirming their item is being prepared.

**Why this priority**: Lowest urgency of the four statuses — it's a "we've got it" confirmation
rather than news the Customer is anxiously awaiting. Included for completeness (every status
transition notifies) but reasonable to build last.

**Independent Test**: Can be fully tested by having a Vendor advance an OrderItem to PROCESSING via
the existing fulfillment endpoint and confirming the Customer receives a corresponding email.

**Acceptance Scenarios**:

1. **Given** a Customer's order item has just been placed, **When** the owning Vendor advances it
   to PROCESSING, **Then** the Customer receives an email identifying the order and the specific
   item, stating it is being prepared.

---

### Edge Cases

- What happens if the Customer's email address has never been verified? Notification still sends —
  order-status updates are informational, not a security-sensitive action subject to the
  email-verification gate used elsewhere in the system (see Assumptions).
- What happens if an attempted status transition is invalid (e.g. skipping a stage, or advancing a
  CANCELLED item) and is rejected by the existing transition rules? No notification is sent, since
  no status change actually occurred.
- What happens if the outbound email transport fails or times out? The status transition itself
  MUST already have succeeded and committed (per Constitution Principle IV, email is a mocked
  edge, not core correctness) — a notification delivery failure MUST NOT undo or block the
  fulfillment status change.
- What happens when the same OrderItem is advanced through multiple statuses in quick succession
  (e.g. PROCESSING → SHIPPED → DELIVERED within seconds, such as in a test or an admin correcting a
  mistake)? Each individual transition sends its own, separate email — no de-duplication or
  batching window.
- What happens for an order placed as a guest, if guest checkout exists? Out of scope — per
  003-cart-checkout, checkout already requires an authenticated Customer account, so every order
  has a registered account email to notify.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The System MUST send an email notification to the Customer who placed the order
  whenever any of that Customer's OrderItems is successfully advanced to PROCESSING, SHIPPED,
  DELIVERED, or CANCELLED.
- **FR-002**: Each notification MUST identify, at minimum, the order and the specific product/line
  item the status change applies to, and the new status reached.
- **FR-003**: The System MUST NOT send a notification when a requested status transition is
  rejected (invalid transition, unauthorized actor, or any other failure) — only actually-applied
  transitions trigger notification.
- **FR-004**: The System MUST send exactly one notification per successful status transition (not
  one per order, and not batched across multiple items or transitions).
- **FR-005**: Notification delivery MUST be decoupled from the status-transition transaction such
  that a notification failure (delivery error, transport unavailable) does not roll back, block, or
  otherwise fail the underlying status change.
- **FR-006**: The System MUST send the notification to the Customer's account email address
  regardless of whether that address has been verified.
- **FR-007**: The System MUST reuse the existing outbound-email notification mechanism (already
  used for verification and password-reset email) rather than introducing a second, parallel
  email-sending mechanism.
- **FR-008**: Notification content for a CANCELLED transition MUST NOT state or imply any
  refund/payment outcome, since payment handling for cancellations is explicitly out of scope
  (per 004-order-fulfillment).
- **FR-009**: This feature covers email notifications only; it MUST NOT introduce SMS/push
  notifications, a notification-preferences or opt-out UI, or real-time in-app (websocket)
  notifications.

### Key Entities

- **OrderItem status transition** (existing entity from 004-order-fulfillment, not modified by this
  feature): the event this feature reacts to — carries the order, the line item, the new status,
  and (transitively) the Customer to notify.
- **Notification** (conceptual, not necessarily a new persisted record): the email sent to a
  Customer as a side effect of one status transition; identified by which order/item/status it
  reports on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successfully applied OrderItem status transitions (PROCESSING, SHIPPED,
  DELIVERED, CANCELLED) result in exactly one notification to the correct Customer.
- **SC-002**: 0% of rejected/invalid status-transition attempts result in a notification being
  sent.
- **SC-003**: A Customer can identify, from the notification alone (without visiting the site),
  which order and which item the update refers to and what its new status is.
- **SC-004**: Simulated notification-delivery failures during testing do not cause any observable
  failure or rollback of the status-transition operation itself.

## Assumptions

- Every Customer account has exactly one email address on file (from 001-accounts-auth), and that
  is the address notified — there is no separate "notification email" or per-order contact email.
- Notifications are informational, not account-security actions, so they are not subject to the
  email-verification gate used elsewhere in the system (e.g. before a shop can be approved).
- "Reuse the existing email notification mechanism" means extending the same outbound-email
  capability already used for verification/reset email with new message types, not standing up a
  second, separate way of sending email — this keeps a single swappable transport per Constitution
  Principle IV.
- No notification-delivery audit log/history is required by this feature; the authoritative record
  of what happened remains the existing `OrderItemStatusEvent` history from 004-order-fulfillment.
- Email content is plain text (matching the existing verification/reset email style), not HTML
  templates — no visual design requirement.
- An Administrator does not receive these Customer-facing notifications; this feature is scoped to
  notifying the Customer only, consistent with 004-order-fulfillment's Vendor/Administrator/Customer
  role split.

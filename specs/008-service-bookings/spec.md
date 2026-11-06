# Feature Specification: Service Bookings

**Feature Branch**: `feature/service-bookings`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Service bookings (feature 008, short name service-bookings). MangiMall sells physical goods; add service businesses (e.g. salons, clinics, garages). An approved shop marked as a services business lists services with price and duration in service categories, and sets weekly opening hours, whole-day closures and capacity. The public can browse services and see open times in Dar es Salaam time. A logged-in customer with a verified email requests an open time; capacity is shared across the shop's services and double booking must be impossible. The provider accepts or declines; the customer pays after acceptance by mobile money or Lipa Namba, and a declined booking is never charged. Unanswered requests and unpaid accepted bookings expire. Failed payments can be retried until the deadline. Customers and providers can cancel; money owed back goes on a list that admins pay by hand and mark as paid. The provider marks a visit completed or no-show, commission is frozen at booking, and earnings flow into existing payouts and finance reports. Default rules: 12h provider response; 6h to pay; at least 3h notice; customer cancels free before payment, full refund up to 24h before the visit once paid, after which they contact support; provider cancellation requires a reason and gives a full refund; paid no-show still earns the provider; one business type per shop; max 3 active unpaid bookings per customer. Out of scope, for later features: rides/transport (009), cash at the visit (010), return trips, service reviews, SMS and reminders, rescheduling, staff calendars, service images, automatic refunds."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Provider lists services and customers find open times (Priority: P1)

A vendor opens a shop and chooses "services" as its business type. Once an Administrator approves the shop, the provider adds services with a name, description, category, price and duration. They set weekly opening hours, any whole days the shop is closed, and how many customers the shop can serve at the same time. Anyone, signed in or not, can browse published services, open one, choose a date and see the open times in Dar es Salaam time.

**Why this priority**: Nothing can be booked until services and open times exist. On its own, this also gives service businesses a public presence in the mall.

**Independent Test**:
1. Register a shop as a services business and have an Administrator approve it.
2. Add and publish a service, then set opening hours.
3. As a guest, find the service and choose a date.
4. Confirm the times shown match the opening hours and that the whole service fits before closing.

**Acceptance Scenarios**:

1. **Given** a vendor opening a shop, **When** they submit the request, **Then** they must choose goods or services, and they cannot change that choice afterwards.
2. **Given** a services shop that is not approved, **When** its owner tries to create, publish or change a service, **Then** the action is refused.
3. **Given** a services shop, **When** its owner tries to add a physical product, **Then** the action is refused. **Given** a goods shop, **When** its owner tries to add a service, **Then** the action is refused.
4. **Given** an approved services shop with no saved location, **When** its owner tries to publish a service, **Then** the action is refused with a message to set the shop's location first.
5. **Given** a published service in an approved shop, **When** anyone views it, **Then** they see its name, description, price, duration and shop.
6. **Given** a 60-minute service and a shop open from 09:00 to 17:00, **When** a customer views a date, **Then** the last time offered is 16:00.
7. **Given** a date the shop has marked as closed, **When** a customer views that date, **Then** no times are offered.
8. **Given** a customer whose device is set to another time zone, **When** they view open times, **Then** the times are still shown in Dar es Salaam time and labelled as such.

---

### User Story 2 - Customer requests a time and the provider responds (Priority: P1)

A signed-in customer with a verified email picks an open time, gives a contact phone number and can add a note. The request holds that time while the provider decides. The provider sees the request in their dashboard and accepts or declines it. The customer can follow its status. A request the provider doesn't answer in time expires, and the time opens up again.

**Why this priority**: This is the core of booking, and the rule that a time can't be double booked lives here.

**Independent Test**:
1. As a customer, request an open time.
2. As the provider, accept it.
3. Confirm the customer sees it as accepted and the time is no longer offered once capacity is full.
4. Repeat with a decline, and confirm no payment is requested and the time opens up again.

**Acceptance Scenarios**:

1. **Given** a guest or a customer with an unverified email, **When** they try to request a time, **Then** they are told to sign in or verify their email first.
2. **Given** a shop serving one customer at a time, **When** two customers request the same time at the same moment, **Then** exactly one request succeeds and the other is told the time is no longer available.
3. **Given** a shop serving one customer at a time, **When** a time overlaps a booking for a different service in that shop, **Then** that time is not offered.
4. **Given** a shop serving two customers at a time, **When** two customers hold a time, **Then** the time stops being offered, and a third request for it is refused.
5. **Given** a customer with 3 active unpaid bookings, **When** they request another, **Then** the request is refused with a clear message.
6. **Given** a time less than 3 hours from now, **When** a customer views or requests it, **Then** it isn't offered and the request is refused.
7. **Given** a customer who owns the shop, **When** they try to book one of its services, **Then** the request is refused.
8. **Given** a new request, **When** the provider declines it, **Then** the booking ends, the customer is told and is never charged, and the time opens up again.
9. **Given** a request the provider hasn't answered by its response deadline, **When** the deadline passes, **Then** the booking is treated as expired, the time opens up and the customer is told.
10. **Given** a request or an accepted unpaid booking, **When** the customer cancels it, **Then** it ends at no charge and the time opens up again.
11. **Given** two customers and two providers, **When** one tries to view another's bookings, **Then** the booking is reported as not found.

---

### User Story 3 - Customer pays after acceptance, and money owed back is tracked (Priority: P1)

Once the provider accepts, the customer has until the payment deadline to pay by mobile money or Lipa Namba. Payment confirms the booking. A failed mobile-money attempt doesn't end the booking, so the customer can retry until the deadline. If a paid booking is later cancelled, the amount owed goes on a list that Administrators pay by hand and mark as paid.

**Why this priority**: Accepted bookings can't be completed without payment, and it's how the mall earns from services. Stories 2 and 3 must reach production together.

**Independent Test**:
1. Have a provider accept a booking.
2. As the customer, pay by mobile money and confirm the booking becomes confirmed.
3. As the provider, cancel it with a reason, and confirm a refund entry appears for the full amount.
4. As an Administrator, mark the refund as paid.

**Acceptance Scenarios**:

1. **Given** an accepted booking, **When** a mobile-money payment succeeds, **Then** the booking is confirmed and both customer and provider are told.
2. **Given** an accepted booking, **When** a mobile-money payment fails, **Then** the booking stays accepted, and the customer can try again until the deadline.
3. **Given** a payment still being processed, **When** the customer tries to pay again or cancel, **Then** the action is refused until that payment settles, so they can't be charged twice.
4. **Given** an accepted booking, **When** the customer submits a Lipa Namba transaction ID, **Then** the time stays held until an Administrator confirms or rejects the payment.
5. **Given** an accepted booking with no payment in progress, **When** its payment deadline passes, **Then** the booking is treated as expired and the time opens up.
6. **Given** a booking that has already expired or been cancelled, **When** a successful payment arrives late, **Then** the booking is not revived unless it can still be honoured, and otherwise the full amount goes on the refund list.
7. **Given** a payment notification with the wrong amount, **When** it arrives, **Then** it is ignored.
8. **Given** a confirmed booking at least 24 hours away, **When** the customer cancels, **Then** the booking ends and the full amount goes on the refund list.
9. **Given** a confirmed booking less than 24 hours away, **When** the customer tries to cancel, **Then** the action is refused and they are told to contact support.
10. **Given** a confirmed booking, **When** the provider cancels without a reason, **Then** the action is refused. **When** they give a reason, **Then** the booking ends, the customer is told, and the full amount goes on the refund list.
11. **Given** any active booking, **When** an Administrator with permission cancels it, **Then** they give a reason and set any amount owed back, up to the amount paid.
12. **Given** an entry on the refund list, **When** an Administrator with finance permission marks it as paid with a reference, **Then** it shows as paid, with who paid it and when, and can't be paid again.

---

### User Story 4 - Provider completes the visit and earns (Priority: P2)

After the visit time has started, the provider marks a confirmed booking as completed or as a no-show. The provider's earning, after the commission set when the booking was requested, then becomes available for payout alongside any goods earnings. Administrators see service bookings in their finance figures, transactions and payout statements.

**Why this priority**: Providers need to get paid, but this comes after bookings can be made and paid for.

**Independent Test**:
1. Complete a paid booking as the provider.
2. Confirm the shop's available balance rises by the booking's earning.
3. As an Administrator, pay the shop out and confirm the statement lists the booking.

**Acceptance Scenarios**:

1. **Given** a confirmed booking whose start time hasn't arrived, **When** the provider tries to mark it completed or no-show, **Then** the action is refused.
2. **Given** a confirmed booking, **When** the provider marks it completed or no-show, **Then** its earning becomes available for payout.
3. **Given** a booking requested at one commission rate, **When** the shop's rate or the service's price later changes, **Then** the booking keeps its original price, commission and earning.
4. **Given** a shop with both goods earnings and booking earnings, **When** its balances are shown, **Then** each figure is the exact sum of both, with nothing counted twice.
5. **Given** a payout that includes bookings, **When** it fails, **Then** those bookings become available for payout again.
6. **Given** a cancelled, declined or expired booking, **When** balances are calculated, **Then** it adds nothing to the provider's earnings.
7. **Given** an Administrator viewing transactions, **When** a payment belongs to a booking, **Then** it is listed with a link to that booking and its commission, and the transaction search and report include it.

---

### Edge Cases

- **Opening hours or capacity change:** existing bookings stay valid; only times not yet booked change.
- **Closure added on a day with bookings:** existing bookings are not cancelled automatically. The provider is warned and must cancel them individually.
- **Service unpublished or archived:** it can't be newly booked, but existing bookings and their history remain.
- **Visit very soon after a request:** response and payment deadlines are shortened so both end before the visit, with the response deadline at least 90 minutes before and the payment deadline at least 60 minutes before.
- **Lipa Namba close to the visit:** it's only offered if the visit is at least 3 hours away, because an Administrator must confirm it.
- **Provider and deadline race:** if an accept, a payment and a deadline happen at the same moment, only one takes effect, and the other person sees the current status.
- **Cleanup running late:** a time opens up as soon as its deadline passes, even if the scheduled cleanup hasn't run. Late cleanup never makes a time wrongly unavailable.
- **Date beyond the booking window:** dates in the past or more than 60 days ahead offer no times.
- **Exactly 24 hours before the visit:** the customer can still cancel for a full refund.
- **Failed notification email:** the booking still proceeds, and the failure is logged.

## Requirements *(mandatory)*

### Functional Requirements

**Shops and services**

- **FR-001**: Every shop MUST have one business type, goods or services. Existing shops MUST be treated as goods, and vendors MUST NOT be able to change the type.
- **FR-002**: Only services shops MUST be able to list services, and only goods shops MUST be able to list products.
- **FR-003**: A shop that isn't approved MUST NOT be able to create, publish or change services, or receive or accept bookings. This MUST be enforced on the server.
- **FR-004**: Providers MUST be able to create, edit, publish, unpublish and archive a service with a name, description, service category, price and duration.
- **FR-005**: Categories MUST be either product or service categories, managed on the existing admin category screens. Products and services MUST only use categories of their own kind.
- **FR-006**: Providers MUST be able to set weekly opening hours with more than one period per day, whole-day closures, and how many customers the shop serves at once.
- **FR-007**: A service MUST NOT be publishable until its shop has a saved location.

**Browsing and open times**

- **FR-008**: Anyone MUST be able to browse and search published services of approved shops, filter by category, and see a shop's services on its page. Lists MUST be paginated.
- **FR-009**: The system MUST offer times in 30-minute steps, only where the whole service fits within an opening period, at least 3 hours ahead and no more than 60 days ahead.
- **FR-010**: All times MUST be shown in Dar es Salaam time and be labelled as such, regardless of the viewer's device settings.

**Requesting and responding**

- **FR-011**: Only a signed-in customer with a verified email MUST be able to request a booking, and MUST provide a contact phone number. They MUST NOT be able to book their own shop's services.
- **FR-012**: Capacity MUST be shared across all of a shop's services. The number of overlapping holding bookings MUST never exceed the shop's capacity, including when requests arrive at the same moment.
- **FR-013**: A time MUST be held by a request before its response deadline, an accepted booking before its payment deadline or with a payment in progress, and a confirmed booking.
- **FR-014**: A customer MUST NOT hold more than 3 active unpaid bookings.
- **FR-015**: Providers MUST be able to see their bookings and accept or decline requests. A shop's bookings MUST be visible only to its owner, the customer who made them, and Administrators with permission.
- **FR-016**: A request MUST expire 12 hours after it's made if unanswered, and an accepted booking MUST expire 6 hours after acceptance if unpaid. Both deadlines MUST be shortened where needed to fall before the visit, and both durations and the 3-hour notice MUST be adjustable without a code change.
- **FR-017**: Expired bookings MUST release their time when the deadline passes. A scheduled cleanup MUST update their status and notify the customer.

**Payment**

- **FR-018**: Payment MUST only be possible after acceptance, by mobile money or Lipa Namba, and a booking MUST NOT be charged before then. Lipa Namba MUST only be offered when the visit is at least 3 hours away.
- **FR-019**: The amount MUST be calculated by the system, never taken from the customer's device.
- **FR-020**: A failed payment MUST allow a retry until the deadline, and a booking MUST have at most one payment in progress or succeeded.
- **FR-021**: A repeated payment notification MUST NOT take effect twice. A late successful payment MUST confirm the booking if it can still be honoured, and otherwise MUST create a refund entry.
- **FR-022**: Administrators with finance permission MUST be able to confirm or reject Lipa Namba payments on bookings.
- **FR-023**: Goods checkout and order payment MUST keep working exactly as they do today.

**Cancellation and refunds**

- **FR-024**: Customers MUST be able to cancel free of charge before payment, except while a payment is in progress, and for a full refund when a confirmed booking is at least 24 hours away. Within 24 hours they MUST be told to contact support.
- **FR-025**: Providers MUST be able to cancel a confirmed booking by giving a reason, which gives the customer a full refund.
- **FR-026**: Administrators with permission MUST be able to cancel any active booking, with a reason and an amount owed back of up to the amount paid.
- **FR-027**: Money owed back MUST appear on a refund list showing the booking, amount, reason and status. Administrators with finance permission MUST be able to mark an entry as paid with a reference, once only. The system MUST NOT send refunds automatically.

**Completion and money**

- **FR-028**: Once the start time has arrived, providers MUST be able to mark a confirmed booking as completed or no-show. A paid no-show MUST still earn the provider.
- **FR-029**: Price, commission and provider earning MUST be fixed when a booking is requested, using the shop's commission rate or the mall's default.
- **FR-030**: Earnings from completed and no-show bookings MUST be included in shop balances, payouts, payout statements, mall finance figures, and the transaction list and report. Goods figures MUST NOT change as a result.
- **FR-031**: A failed payout MUST release its bookings to be paid out again.

**Notifications, history and oversight**

- **FR-032**: The system MUST email the provider about new requests, customer cancellations and confirmed payments, and email the customer about acceptance, decline, confirmation, expiry and cancellation. A failed email MUST NOT stop the booking.
- **FR-033**: Booking pages MUST update without a manual refresh when a booking's status changes.
- **FR-034**: Every booking status change MUST be kept as a permanent history with its time, and Administrators' actions and refund payments MUST appear in the audit log.
- **FR-035**: Administrators with permission MUST be able to view and filter all bookings, and each admin action MUST check the permissions of the Administrator's tier.

### Key Entities

- **Service**: Something a services shop offers, with a name, description, category, price and duration. It can be published, unpublished or archived.
- **Opening Hours**: The periods a shop is open on a weekday, in Dar es Salaam time.
- **Shop Closure**: A whole date when a shop is closed.
- **Booking**: A customer's request for a service at a time. It holds its status, deadlines, contact phone, note, and fixed price, commission and earning. Its status is requested, awaiting payment, confirmed, completed, no-show, declined, expired or cancelled.
- **Booking Status Event**: A permanent record of one status change.
- **Booking Payment**: An attempt to pay for a booking. A booking can have several failed attempts, but only one in progress or succeeded.
- **Refund Entry**: Money the mall owes a customer, with its amount, reason and status (due or paid), and who paid it, when and with what reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a test of simultaneous requests for one time, the number of accepted requests never exceeds the shop's capacity across repeated runs.
- **SC-002**: A customer can find a service and submit a request in under 3 minutes.
- **SC-003**: No declined, expired or customer-cancelled unpaid booking results in a charge.
- **SC-004**: Every payment that succeeds ends in either a confirmed booking or a refund entry, with none left unrecorded.
- **SC-005**: For a shop with both goods and bookings, every balance figure equals the exact sum of its goods and booking amounts, and payouts match to the shilling.
- **SC-006**: A time opens up within one minute of its deadline passing, whether or not the scheduled cleanup has run.
- **SC-007**: All existing goods checkout, payment and finance tests pass unchanged.
- **SC-008**: Times are correct in Dar es Salaam time around midnight, in every tested device time zone.
- **SC-009**: Every attempt by an unauthorised person to view or change a booking is refused.

## Assumptions

- **Reused systems:** accounts, email verification, shop approval, categories, mobile money, Lipa Namba, commission, payouts, audit log and live updates all already exist.
- **Launch timing:** this feature launches publicly only with rides (feature 009). Stories 2 and 3 must reach production together, because accepted bookings can't otherwise be paid for.
- **Live payments:** real money depends on the mobile-money and payout setup being completed. Until then, payments run in the existing test modes.
- **Goods shops:** a business offering both goods and services uses a separate shop for each. Existing goods shops don't move or change.
- **Capacity:** each shop has one capacity figure; staff calendars and per-service capacity are out of scope.
- **Booking window:** the 60-day limit and 30-minute step are chosen defaults that can be adjusted later.
- **Refunds:** Administrators send money by hand outside the system. Refund timing and staffing are an operational decision.
- **Time zone:** the mall serves Dar es Salaam, so one market time zone applies to all shops.
- **Provider completion:** a provider who never marks a visit doesn't get paid for it. There is no automatic completion in this feature.
- **Out of scope:** rides and transport (009), cash at the visit (010), return trips, service reviews, SMS and reminders, rescheduling, staff calendars, service images, and automatic refunds.

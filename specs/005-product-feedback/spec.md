# Feature Specification: Product Feedback & Reviews

**Feature Branch**: `005-product-feedback`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Product feedback and reviews: customers who have purchased a product can leave a star rating and written review on it; reviews are visible on the product detail page to all shoppers; vendors can view feedback on their own shop's products; administrators can moderate (remove) inappropriate reviews. Scope follows the project constitution's three-role model (Customer, Vendor, Administrator) and the existing 001-004 features (accounts-auth, product-catalog, cart-checkout, order-fulfillment) it builds on top of."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer leaves a rating and review on a purchased product (Priority: P1) 🎯 MVP

A Customer who has actually received a product wants to record a star rating and, optionally, a
written comment about it, so their experience is captured and other shoppers can see it.

**Why this priority**: This is the entire feature — without the ability to leave feedback, there
is nothing for vendors to view, nothing for shoppers to read, and nothing for administrators to
moderate. Every other story depends on feedback existing.

**Independent Test**: As a Customer with an order line item for a product that has reached
DELIVERED status, open that product's page, submit a star rating (with or without written text),
and confirm the review is saved and attributed to that customer.

**Acceptance Scenarios**:

1. **Given** a Customer whose order line item for a product is DELIVERED, **When** they submit a
   star rating and written comment for that product, **Then** the review is saved and associated
   with that customer and product.
2. **Given** a Customer whose order line item for a product is DELIVERED, **When** they submit
   only a star rating with no written comment, **Then** the review is saved successfully (written
   text is optional).
3. **Given** a Customer who has never had an order line item for a product, **When** they attempt
   to submit a review for that product, **Then** the system rejects the submission.
4. **Given** a Customer who already left a review on a product, **When** they submit another
   review for the same product, **Then** the system updates their existing review rather than
   creating a second one for the same customer/product pair.
5. **Given** a Customer editing their own existing review, **When** they change the rating or
   text and save, **Then** the review reflects the updated content.

---

### User Story 2 - Shoppers see reviews on the product detail page (Priority: P1)

Any shopper browsing the catalog — logged in or not — wants to see other customers' ratings and
comments on a product before deciding to buy it.

**Why this priority**: Feedback only creates value once it's visible to the people deciding
whether to buy; this closes the loop from User Story 1 and ships in the same increment so the
feature is demonstrably useful end to end.

**Independent Test**: As any shopper (including a logged-out visitor), open a product page that
has at least one review and confirm the rating and comment are visible, along with an aggregate
average rating and review count for that product.

**Acceptance Scenarios**:

1. **Given** a product with one or more reviews, **When** any shopper opens that product's detail
   page, **Then** they see each review's rating, written comment (if any), and the reviewing
   customer's display name, plus the product's average rating and total review count.
2. **Given** a product with no reviews yet, **When** a shopper opens that product's detail page,
   **Then** the page indicates there are no reviews yet rather than erroring or showing a broken
   rating.
3. **Given** a product with reviews, **When** a new review is submitted or an existing one is
   edited, **Then** the product's average rating and review count reflect the change on the next
   page load.

---

### User Story 3 - Vendor views feedback on their own shop's products (Priority: P2)

A Vendor wants to read the ratings and comments customers have left on their shop's products, to
understand how their products are being received.

**Why this priority**: Valuable to vendors for understanding product reception, but the platform
already delivers the core value (customers leaving feedback, shoppers reading it) without this
view — vendors can technically see reviews on the public product page already, so this story adds
a scoped, shop-centric view rather than new capability.

**Independent Test**: As a Vendor with an APPROVED shop, open a feedback view scoped to that
shop's products and confirm reviews across all of that shop's products are visible, with no
review belonging to another vendor's shop appearing.

**Acceptance Scenarios**:

1. **Given** a Vendor with an APPROVED shop whose products have received reviews, **When** the
   Vendor opens their feedback view, **Then** they see every review left on their own shop's
   products, including which product each review is for.
2. **Given** a Vendor viewing their feedback, **When** they look for a way to edit or delete a
   customer's review from this view, **Then** no such control exists — vendors can read feedback
   but cannot alter or remove it.
3. **Given** two vendors each with reviewed products, **When** Vendor A opens their feedback
   view, **Then** they see only reviews on their own shop's products, never Vendor B's.

---

### User Story 4 - Administrator moderates inappropriate reviews (Priority: P3)

An Administrator wants to remove a review that violates platform standards (e.g. abusive
language, spam, unrelated content), to keep product feedback trustworthy and safe.

**Why this priority**: Moderation protects the integrity of a feature that's already delivering
value by Stories 1-2; it's important but not required for the core feedback loop to function on
day one.

**Independent Test**: As an Administrator, open the review moderation view, locate a specific
review, remove it, and confirm it no longer appears on the product's detail page or in any
customer/vendor/shopper view.

**Acceptance Scenarios**:

1. **Given** an existing review, **When** an Administrator removes it, **Then** the review is no
   longer visible anywhere (product page, vendor feedback view) and the product's average rating
   and review count are recalculated without it.
2. **Given** an Administrator viewing the moderation list, **When** they browse reviews across all
   products and shops, **Then** they can see the review text, rating, reviewing customer, and
   product/shop it belongs to, in one place.
3. **Given** a review removed by an Administrator, **When** the reviewing Customer opens the
   product page again, **Then** the system treats them as not having reviewed that product (they
   are able to submit a new review if they still have a qualifying purchase).

---

### Edge Cases

- What happens when a Customer's order line item for a product is later CANCELLED after they've
  already left a review (e.g. a different line item on a different order for the same product was
  the qualifying purchase, and that one gets cancelled)? As long as the Customer has at least one
  other DELIVERED line item for that product, the review remains valid; the review is not
  automatically removed by an order cancellation.
- What happens when a Customer tries to review a product before any of their order line items for
  it have reached DELIVERED (e.g. it's still PROCESSING or SHIPPED)? The system MUST reject the
  submission until a qualifying DELIVERED line item exists.
- What happens when a product is removed from the catalog (soft-deleted) after receiving reviews?
  Existing reviews are preserved (for the Vendor's and Administrator's records) but the product
  page is no longer publicly reachable, per the existing catalog feature's own soft-delete
  behavior.
- What happens when an Administrator removes a review and the same customer later becomes
  re-eligible (a new DELIVERED line item for the same product)? They can submit a fresh review,
  which is treated as new feedback, not a restoration of the removed one.
- How does the system handle a rating with no written comment when computing the average rating
  and review count? The rating alone counts toward both the average and the count; written text
  is purely supplementary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a Customer to submit a star rating (on a fixed 1-5 scale) and an
  optional written comment for a product, only if that Customer has at least one order line item
  for that product with status DELIVERED.
- **FR-002**: System MUST reject a review submission from a Customer who has no DELIVERED order
  line item for the product being reviewed.
- **FR-003**: System MUST allow at most one review per Customer per product; a repeat submission
  by the same Customer for the same product MUST update their existing review rather than create
  an additional one.
- **FR-004**: System MUST allow a Customer to edit or delete their own review at any time.
- **FR-005**: System MUST display, on the public product detail page, every non-removed review for
  that product (rating, optional written comment, reviewing customer's display name) to any
  shopper regardless of authentication status.
- **FR-006**: System MUST compute and display, on the public product detail page, the product's
  average rating and total review count, recalculated whenever a review is added, edited, or
  removed.
- **FR-007**: System MUST allow a Vendor to view all reviews left on products belonging to their
  own shop(s), including which product each review belongs to.
- **FR-008**: System MUST NOT allow a Vendor to edit, delete, or otherwise alter another user's
  review through the vendor feedback view.
- **FR-009**: System MUST reject any attempt by a Vendor to view reviews scoped to a shop they do
  not own.
- **FR-010**: System MUST allow an Administrator to view all reviews across every product and
  shop, including the review's text, rating, reviewing customer, and the product/shop it belongs
  to.
- **FR-011**: System MUST allow an Administrator to remove any review; once removed, the review
  MUST NOT appear on the product detail page, in the vendor feedback view, or in review counts/
  averages.
- **FR-012**: System MUST NOT allow a Customer or Vendor to remove another Customer's review;
  removal by non-owners is an Administrator-only capability.
- **FR-013**: A Vendor's ability to view feedback on their shop's products MUST be independent of
  that shop's current approval status (Constitution Principle II governs selling/listing
  capability, not read access to feedback already received while the shop was approved).

### Key Entities

- **Review**: One Customer's feedback on one Product — a 1-5 star rating, an optional written
  comment, the reviewing Customer, the reviewed Product, and timestamps for creation/last edit.
  At most one Review exists per (Customer, Product) pair. A Review references, but does not embed,
  the DELIVERED order line item that qualified the Customer to leave it.
- **Product Rating Summary**: The derived average rating and total review count for a Product,
  computed from its non-removed Reviews; recalculated on every Review add/edit/remove rather than
  stored as independent state a Review update could desync from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Customer with a qualifying DELIVERED purchase can submit a review in a single
  action without needing to locate their order first.
- **SC-002**: 100% of review submission attempts from customers without a DELIVERED order line
  item for that product are rejected, and no unauthorized review is ever stored.
- **SC-003**: Any shopper, including one who is not logged in, can see a product's reviews and
  aggregate rating on that product's detail page with no additional navigation.
- **SC-004**: A Vendor can view every review across their own shop's products from a single view,
  with zero reviews belonging to another vendor's shop appearing in it.
- **SC-005**: An Administrator can locate and remove any single review, after which it is absent
  from every customer-, shopper-, and vendor-facing view and excluded from the product's average
  rating and count, with no manual recalculation step required.
- **SC-006**: 100% of Customer/Product pairs have at most one stored review at any time, with no
  duplicate reviews created by repeated submission.

## Assumptions

- "Purchased" is interpreted as the strongest existing verified-purchase signal already in the
  system: an `OrderItem` for that product, belonging to that Customer, with status DELIVERED
  (reusing 004-order-fulfillment's fulfillment lifecycle) — not merely a placed order, since
  PROCESSING/SHIPPED lines don't yet represent a completed transaction the customer can honestly
  review.
- Rating scale is a fixed integer 1-5 stars, the near-universal e-commerce convention; no
  half-star or numeric free-text scale is introduced.
- A review is per (Customer, Product) pair, not per individual order or order line item — a
  Customer who orders the same product twice still has one review slot for it, which they can
  update.
- No vendor response/reply-to-review capability is introduced in this feature; vendors have
  read-only visibility (User Story 3). Vendor responses are a possible future feature.
- No review-helpfulness voting, photo/image attachments, or verified-purchase badge display beyond
  the existing gate itself are in scope for this feature.
- Removing a review is a hard delete from all customer/shopper/vendor-facing views and from rating
  calculations; this feature does not introduce a separate "hidden but retained" moderation state
  or an appeal workflow.
- No notifications (email/in-app) are sent to the Customer, Vendor, or reviewer when a review is
  submitted, edited, or removed — consistent with 004-order-fulfillment's same assumption that
  notification delivery is a separate future feature.
- This feature extends the existing public product detail page (delivered by
  002-product-catalog) to show reviews rather than introducing a new customer-facing page for
  that purpose; the Vendor and Administrator feedback views are new pages, scoped analogously to
  the existing vendor/admin order views from 004-order-fulfillment.

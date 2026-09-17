# Feature Specification: Product Catalog

**Feature Branch**: `002-product-catalog`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Product catalog: approved vendors can create, edit, publish, and unpublish product listings within their approved shop(s) (name, description, price, stock quantity, category, images); unapproved or rejected shops cannot create or publish listings (enforced server-side per Constitution Principle II). Customers can browse/search/filter published products across all vendors and view a single product's detail page. Vendors can only manage listings belonging to their own shop(s). Stock quantity must decrement correctly later at checkout (out of scope for this feature, but the data model must support it per Constitution Principle IV/VI)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendor manages products in an approved shop (Priority: P1)

A Vendor with at least one APPROVED shop creates a product listing (name, description, price,
stock quantity, category, images), edits its details, and publishes it so customers can see it.
They can later unpublish it (e.g. to pause sales) or edit it again without losing its history.

**Why this priority**: This is the core capability the whole feature exists for — without vendors
being able to list products, there is no catalog for anyone to browse. It depends on the shop
approval gate delivered in 001-accounts-auth but adds nothing else, so it is independently
demonstrable and valuable on its own.

**Independent Test**: Can be fully tested by logging in as a Vendor with an APPROVED shop,
creating a product, confirming it does not appear anywhere public until published, publishing it,
confirming it now appears in that shop's product list, editing a field, and unpublishing it —
delivers a working vendor-side catalog management flow independent of customer browsing.

**Acceptance Scenarios**:

1. **Given** a Vendor with an APPROVED shop, **When** they create a product with a valid name,
   description, price, stock quantity, and category, **Then** the product is created in
   `DRAFT`/unpublished state, visible to the Vendor, and not visible to Customers.
2. **Given** a Vendor's unpublished or published product, **When** they edit its name, description,
   price, stock quantity, category, or images, **Then** the changes are saved and reflected
   immediately to the Vendor and, if published, to Customers.
3. **Given** a Vendor's unpublished product with all required fields filled in, **When** they
   publish it, **Then** its status becomes published and it becomes visible in that shop's product
   list and in catalog browsing/search.
4. **Given** a Vendor's published product, **When** they unpublish it, **Then** it is immediately
   removed from catalog browsing/search and from the shop's public product list, but its data and
   history are retained (not deleted).
5. **Given** a Vendor with multiple shops, **When** they view or manage products, **Then** they only
   see and can only act on products belonging to shops they own.

---

### User Story 2 - Unapproved or rejected shop is blocked from listing products (Priority: P1)

A Vendor whose shop is still PENDING, or was REJECTED, attempts to create or publish a product
under that shop and is blocked, with a clear reason, enforced on the server regardless of what the
client UI shows.

**Why this priority**: This directly enforces Constitution Principle II (Vendor Approval Gate),
which is explicitly non-negotiable. It must ship alongside vendor product management (P1) so the
gate can never be bypassed once creation exists — shipping catalog creation without this check,
even temporarily, would violate the constitution.

**Independent Test**: Can be fully tested by attempting to create or publish a product under a
PENDING or REJECTED shop via a direct API call (bypassing the UI) and confirming the server rejects
it — delivers a demonstrable, UI-independent proof the gate holds.

**Acceptance Scenarios**:

1. **Given** a Vendor whose shop is PENDING, **When** they attempt to create a product under that
   shop, **Then** the request is rejected with a clear "shop not approved" message and no product is
   created.
2. **Given** a Vendor whose shop is REJECTED, **When** they attempt to create or publish a product
   under that shop, **Then** the request is rejected the same way.
3. **Given** a Vendor with one APPROVED shop and one PENDING shop, **When** they create a product
   under the APPROVED shop, **Then** it succeeds, proving the gate is enforced per-shop, not
   per-account.
4. **Given** a shop that was APPROVED and later has a published product, **When** an Administrator
   were to change that shop's status away from APPROVED (handled by 001-accounts-auth), **Then**
   the shop's existing published products are no longer eligible for new customer-facing display
   (see Assumptions for exact behavior).

---

### User Story 3 - Customer browses, searches, and filters the catalog (Priority: P2)

A Customer (or an anonymous visitor) browses the full catalog of published products across all
vendors, searches by keyword, filters by category and price range, and opens a single product's
detail page to see its full description, price, stock availability, images, and the shop that
sells it.

**Why this priority**: This is the demand side of the catalog — it delivers the customer-facing
value of everything vendors publish in P1, and is what makes the feature a marketplace rather than
a vendor-only back office. It depends on published products existing (P1) but is independently
testable once even one product is published.

**Independent Test**: Can be fully tested by publishing a handful of products across two different
shops, then as an anonymous or Customer session: browsing the full list, searching for a keyword
that matches one product's name/description, filtering by category and by price range, and opening
one product's detail page — delivers a demonstrable browsing experience independent of vendor
management.

**Acceptance Scenarios**:

1. **Given** multiple published products across multiple shops, **When** a Customer opens the
   catalog, **Then** they see all published products, and only published products (no
   drafts/unpublished, no products from PENDING/REJECTED shops).
2. **Given** a keyword that matches a product's name or description, **When** a Customer searches
   with that keyword, **Then** matching published products are returned and non-matching ones are
   not.
3. **Given** products across multiple categories and price points, **When** a Customer filters by
   a category and/or a price range, **Then** only published products meeting all selected filters
   are returned.
4. **Given** a published product, **When** a Customer opens its detail page, **Then** they see its
   name, description, price, category, images, current stock availability (in stock / out of
   stock, not necessarily the exact count), and the name of the shop selling it.
5. **Given** a product with zero stock quantity, **When** a Customer views the catalog or the
   product detail page, **Then** the product is shown as out of stock rather than hidden, so
   customers can still discover it.

---

### Edge Cases

- What happens when a Vendor tries to publish a product missing a required field (e.g. no price or
  no category)? The system MUST reject the publish action with a clear message identifying the
  missing field(s); saving as an unpublished draft with incomplete fields is still allowed.
- What happens when a Vendor sets stock quantity to zero on a published product? The product stays
  published and visible, but shows as out of stock (per User Story 3, Scenario 5) rather than being
  auto-unpublished.
- What happens when a Vendor sets a negative price or negative stock quantity? The system MUST
  reject the input as invalid.
- What happens when a Customer searches or filters and no products match? The system MUST return an
  empty result set with a clear "no products found" indication, not an error.
- What happens when a Vendor deletes a product that has never been published vs. one that has been
  published before? Both are allowed to be deleted (soft-deleted, not exposed to customers), but see
  Assumptions for whether hard delete is permitted once a product has ever been published.
- What happens when two vendors in different shops create products with the same name? This MUST be
  allowed — product names are unique per shop, not globally.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a Vendor to create a product listing under any shop they own that
  is currently APPROVED, capturing name, description, price, stock quantity, category, and zero or
  more images.
- **FR-002**: System MUST reject product creation or publishing under a shop that is not currently
  APPROVED (PENDING or REJECTED), enforced server-side, independent of any client-side UI state.
- **FR-003**: System MUST let a Vendor edit any field of a product belonging to a shop they own,
  regardless of the product's published state.
- **FR-004**: System MUST let a Vendor explicitly publish a product only when all required fields
  (name, description, price, stock quantity, category) are present and valid.
- **FR-005**: System MUST let a Vendor unpublish a previously published product at any time, which
  immediately removes it from customer-facing browsing/search/detail access without deleting its
  data.
- **FR-006**: System MUST scope all Vendor product-management actions (create, edit, publish,
  unpublish, delete, view) to only products belonging to shop(s) the acting Vendor owns.
- **FR-007**: System MUST expose a catalog listing to Customers and anonymous visitors containing
  only published products from shops that are currently APPROVED.
- **FR-008**: System MUST let Customers/visitors search the catalog by keyword matched against
  product name and description.
- **FR-009**: System MUST let Customers/visitors filter the catalog by category and by price range,
  usable together with search and with each other.
- **FR-010**: System MUST let Customers/visitors view a single published product's detail page
  showing name, description, price, category, images, stock availability status, and the selling
  shop's name.
- **FR-011**: System MUST display a product with zero stock quantity as "out of stock" rather than
  hiding it from browsing/search/detail views.
- **FR-012**: System MUST reject product price or stock quantity values that are negative.
- **FR-013**: System MUST enforce product name uniqueness per shop (not globally across the
  marketplace).
- **FR-014**: System MUST let a Vendor delete a product belonging to a shop they own; the product
  MUST no longer be creatable/visible in any customer-facing view once deleted.
- **FR-015**: System MUST record, per product, the stock quantity as a discrete, decrementable
  counter (not a boolean or enum), so a later checkout feature can decrement it per Constitution
  Principle IV/VI without a data-model change.

### Key Entities *(include if feature involves data)*

- **Product**: A listing owned by exactly one Shop. Attributes: name (unique within its shop),
  description, price, stock quantity, category, one or more images, published state
  (draft/published), created/updated timestamps. Relationships: belongs to one Shop; a Shop may
  have many Products.
- **Category**: A classification a Product belongs to, used for browsing and filtering. Products
  reference exactly one Category.
- **Shop** *(existing entity from 001-accounts-auth, referenced not redefined here)*: Owns zero or
  more Products; a Product can only be created or published while its owning Shop's status is
  APPROVED.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Vendor with an approved shop can create and publish a new product in under 2
  minutes.
- **SC-002**: 100% of product-creation and product-publish attempts against a non-APPROVED shop are
  rejected server-side, with zero exceptions, verified independent of the client UI.
- **SC-003**: A Customer can find a specific known product via search or category+price filtering
  in under 15 seconds of interaction.
- **SC-004**: Catalog browsing, search, and filter results contain zero unpublished products or
  products from non-APPROVED shops in 100% of sampled checks.
- **SC-005**: 95% of Customers viewing a product detail page can correctly state its price, stock
  availability, and selling shop without needing to look elsewhere.

## Assumptions

- A product's published state is independent of its shop's approval state at the data level, but
  visibility is the AND of both: a product is only ever shown to customers when it is published AND
  its owning shop is currently APPROVED. If a shop is later un-approved (e.g. an Administrator
  reverses approval — mechanism owned by 001-accounts-auth), its products remain in the database
  unchanged but immediately stop appearing in customer-facing views; no separate cascade/delete
  step is required for this feature.
- One Category set is global/shared across the marketplace (not per-vendor custom categories);
  category management (creating/editing the list of categories) is an Administrator capability
  out of scope for this feature and assumed to be seeded/pre-existing.
- Product images are stored as uploaded files/URLs; image storage backend (local disk, cloud
  bucket) is an implementation detail deferred to planning, consistent with Constitution Principle
  IV (Real Core, Mocked Edges) treating non-core storage as swappable.
- "Delete" removes a product from all customer-facing and vendor-facing views but is a soft delete
  at the data level (not a hard DB row delete), preserving referential integrity for any future
  order history that may reference it — consistent with per-line-item order fulfillment being a
  load-bearing structural element per Constitution Principle VI.
- Stock quantity decrement itself (the write path triggered by checkout) is explicitly out of
  scope for this feature per the user's description; this feature only guarantees the data model
  supports it.
- Reviews/ratings, wishlists, and product recommendations are out of scope for this feature.

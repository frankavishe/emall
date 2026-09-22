# Feature Specification: Role-Aware Homepage & Shared Navigation

**Feature Branch**: `006-homepage-navigation`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "Add a role-aware homepage and shared navigation to the mall app. Today the homepage at "/" is unmodified Next.js boilerplate with no awareness of who's visiting, and there is no shared nav/header anywhere in the app, so users can't navigate except by typing URLs directly. Build a single unified homepage at "/" that shows different content depending on who is visiting, plus a shared role-aware navigation bar used across the app: Guest (not logged in) sees a marketing/landing view with product highlights and Login/Register calls to action; Customer sees a shop-style homepage with featured/recent products and links to cart/orders; Vendor sees a summary view with their shop's approval status, recent orders for their shop, and a link to manage products; Administrator sees a summary view with the count of shops pending approval, recent orders across the platform, and links into admin pages. The nav bar's links must change based on the visitor's role. This is a UI/content feature: prefer reusing existing data already exposed by current pages/endpoints over introducing new backend endpoints. Role checks shown in the UI are a convenience only — server-side role enforcement must remain the source of truth, and the existing three-role model (Customer, Vendor, Administrator) and shop approval state machine must not change."

## Clarifications

### Session 2026-09-22

- Q: After a user logs in or registers, should they land on the new role-aware homepage, or stay on the existing account page as they do today? → A: Redirect to the homepage (`/`) after login/register.
- Q: For a Vendor whose shop application was rejected, should the homepage let them resubmit/re-request a shop directly, or just show the rejected status with a link to the account page where shop requests already happen? → A: Homepage shows status only, with a link to the account page's existing request/resubmit form.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guest visitor lands on a welcoming homepage (Priority: P1) 🎯 MVP

A first-time or logged-out visitor opens the site and, instead of a blank placeholder page, sees a
marketing-style homepage that highlights products available in the mall and makes it obvious how
to log in or create an account.

**Why this priority**: The homepage is currently unbuilt boilerplate — this is the front door of
the entire application. Without this, first impressions and conversion to login/register are
broken for every visitor, logged in or not.

**Independent Test**: As a logged-out visitor, open the homepage and confirm it shows product
highlights and visible Login/Register calls to action, with no errors and no placeholder content.

**Acceptance Scenarios**:

1. **Given** a visitor who is not logged in, **When** they open the homepage, **Then** they see a
   marketing/landing view with a selection of product highlights and clearly visible Login and
   Register calls to action.
2. **Given** a visitor who is not logged in, **When** they open the homepage, **Then** they see no
   vendor-only or administrator-only information (e.g., shop approval status, order data).
3. **Given** the catalog currently has no products, **When** a logged-out visitor opens the
   homepage, **Then** they still see the marketing view and Login/Register CTAs without errors,
   with an empty state in place of product highlights.

---

### User Story 2 - Any visitor navigates the app via a shared, role-aware nav bar (Priority: P1)

A visitor — guest, customer, vendor, or administrator — wants to move around the app (browse
products, check their cart, manage their shop, review pending approvals) from any page, without
knowing or typing exact URLs.

**Why this priority**: There is currently no navigation chrome anywhere in the app; every page is
a dead end reachable only by typed URL. This is as foundational as the homepage itself and ships
in the same increment.

**Independent Test**: As each of the four visitor types (guest, customer, vendor, administrator),
load any page in the app and confirm the navigation bar is present and its links match what that
visitor type is expected to reach.

**Acceptance Scenarios**:

1. **Given** a logged-out visitor, **When** they view the navigation bar on any page, **Then**
   they see links appropriate to a guest (e.g., browse products, Login, Register) and no links to
   cart, orders, vendor, or admin areas.
2. **Given** a logged-in Customer, **When** they view the navigation bar, **Then** they see links
   to browse products, their cart, and their orders, and no vendor- or admin-only links.
3. **Given** a logged-in Vendor, **When** they view the navigation bar, **Then** they see a link to
   manage their products (and other vendor-relevant links), and no admin-only links.
4. **Given** a logged-in Administrator, **When** they view the navigation bar, **Then** they see
   links into admin pages (shop approvals, order oversight), and no customer- or vendor-only
   shopping links.
5. **Given** any visitor, **When** they navigate from the homepage to another page and back,
   **Then** the navigation bar remains present and consistent across pages.

---

### User Story 3 - Customer sees a personalized shopping homepage (Priority: P2)

A logged-in Customer opens the homepage and, instead of a generic marketing view, sees featured or
recently added products along with quick access to their cart and their orders.

**Why this priority**: Customers are the primary transacting users; giving them a homepage that
gets them shopping faster (rather than the guest marketing view) is high value but depends on
User Story 1/2 existing first.

**Independent Test**: Log in as a Customer, open the homepage, and confirm it shows featured/recent
products and links to cart and orders instead of the guest marketing view.

**Acceptance Scenarios**:

1. **Given** a logged-in Customer, **When** they open the homepage, **Then** they see a selection
   of featured or recently added products and links to their cart and their orders.
2. **Given** a logged-in Customer, **When** they open the homepage, **Then** they do not see the
   guest Login/Register CTAs or any vendor/admin-only information.
3. **Given** a logged-in Customer whose cart or order history is empty, **When** they open the
   homepage, **Then** the cart/orders links are still present and functional, without errors.

---

### User Story 4 - Vendor sees a business summary homepage (Priority: P2)

A logged-in Vendor opens the homepage and sees, at a glance, their shop's current approval status,
their shop's recent orders, and a way to get to product management.

**Why this priority**: Vendors need a fast operational overview of their shop; this is high value
for the vendor role but is scoped after the guest/nav foundation and alongside the customer view.

**Independent Test**: Log in as a Vendor and confirm the homepage shows their shop's approval
status, a list of their shop's recent orders, and a link to manage products.

**Acceptance Scenarios**:

1. **Given** a logged-in Vendor whose shop is APPROVED, **When** they open the homepage, **Then**
   they see their shop's approval status as approved, a list of recent orders for their shop, and
   a link to manage their products.
2. **Given** a logged-in Vendor whose shop is PENDING, **When** they open the homepage, **Then**
   they see their shop's status as pending approval, and order/product-management content is not
   presented as if the shop were already active.
3. **Given** a logged-in Vendor whose shop was REJECTED, **When** they open the homepage, **Then**
   they see their shop's status as rejected along with a link to the account page, where the
   existing shop request/resubmission form lives; the homepage itself does not host that form.
4. **Given** a logged-in Vendor with no orders yet, **When** they open the homepage, **Then** the
   recent orders section shows an empty state rather than an error.

---

### User Story 5 - Administrator sees an operational summary homepage (Priority: P3)

A logged-in Administrator opens the homepage and sees how many shops are awaiting approval and a
view of recent orders across the platform, with links into the relevant admin pages.

**Why this priority**: Useful operational visibility for administrators, but there are typically
far fewer administrators than customers/vendors, so this rounds out the feature last.

**Independent Test**: Log in as an Administrator and confirm the homepage shows the count of
shops pending approval, a list of recent platform-wide orders, and links to shop approvals and
order oversight pages.

**Acceptance Scenarios**:

1. **Given** shops are currently pending approval, **When** an Administrator opens the homepage,
   **Then** they see the count of shops pending approval and a link to the shop approvals page.
2. **Given** no shops are currently pending approval, **When** an Administrator opens the
   homepage, **Then** they see a count of zero rather than an error or missing section.
3. **Given** recent orders exist on the platform, **When** an Administrator opens the homepage,
   **Then** they see a list of recent orders across the platform and a link to the order
   oversight page.

---

### Edge Cases

- What happens when a Vendor has not yet requested a shop at all (no shop record)? The homepage
  must prompt them toward requesting a shop rather than showing a broken or empty summary.
- What happens when product, order, or shop-approval data fails to load (e.g., network error)?
  The affected section shows a clear error/retry state rather than a blank area or crash, and
  the rest of the homepage remains usable.
- What happens when a user's session expires while they are on the homepage? The homepage
  reflects the guest (logged-out) view on next load/refresh rather than showing stale
  role-specific data.
- What happens when a logged-out visitor manually navigates to a role-restricted page via a
  known URL? Server-side access control continues to apply regardless of what the nav bar
  displays; the visitor is redirected/denied per existing enforcement.
- How does the homepage behave while data is still loading? Each section shows a loading state
  rather than empty or broken content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST present a single homepage at the site's root address whose content
  varies based on the visitor's authentication state and role (guest, Customer, Vendor,
  Administrator).
- **FR-002**: For a logged-out visitor, the homepage MUST display a marketing/landing view
  including product highlights and Login and Register calls to action.
- **FR-003**: For a logged-in Customer, the homepage MUST display featured/recent products and
  links to their cart and their orders, and MUST NOT display the guest Login/Register CTAs or any
  Vendor- or Administrator-only information.
- **FR-004**: For a logged-in Vendor, the homepage MUST display their shop's current approval
  status, a list of recent orders for their shop, and a link to manage their products.
- **FR-005**: For a logged-in Vendor who has not requested a shop, or whose shop was rejected, the
  homepage MUST prompt them toward the account page's existing shop request/resubmission form
  (not host that form itself) instead of showing an empty or broken summary.
- **FR-006**: For a logged-in Administrator, the homepage MUST display the count of shops
  currently pending approval, a list of recent orders across the platform, and links to the shop
  approvals and order oversight pages.
- **FR-007**: The system MUST provide a shared navigation element present on every page of the
  application, not only the homepage.
- **FR-008**: The navigation element's links MUST reflect the current visitor's role: a guest
  MUST NOT see links exclusive to Customers, Vendors, or Administrators, and each authenticated
  role MUST NOT see links exclusive to a different role.
- **FR-009**: Role-based content shown on the homepage and navigation MUST be treated as a
  presentation convenience only; existing server-side access control for role-restricted pages
  MUST remain the sole enforcement mechanism and MUST NOT be weakened or bypassed by this
  feature.
- **FR-010**: The homepage and navigation MUST NOT alter the existing three-role model (Customer,
  Vendor, Administrator) or the existing shop approval state machine (pending/approved/rejected).
- **FR-011**: Every homepage section that depends on data (products, orders, shop status,
  pending-approval count) MUST show an explicit loading state while fetching and an explicit
  empty state when there is no data, rather than appearing blank or erroring.
- **FR-012**: Every homepage section that depends on data MUST show a clear error/retry
  indication if that data fails to load, without preventing the rest of the homepage from
  rendering.
- **FR-013**: When a logged-in user's session expires or ends, the homepage MUST revert to the
  logged-out (guest) view on next load rather than continuing to show role-specific data.
- **FR-014**: Upon successful login or registration, the system MUST redirect the user to the
  homepage rather than the existing account page.

### Key Entities

This feature is a presentation layer over data that already exists; it introduces no new
entities. It reads from:

- **User** — to determine the visitor's authentication state and role.
- **Shop** — to determine a Vendor's approval status and to count shops pending approval for
  Administrators.
- **Product** — to source featured/recent product highlights shown to guests and Customers.
- **Order** — to source recent-orders summaries shown to Vendors and Administrators.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time, logged-out visitor can identify how to log in or register within 5
  seconds of the homepage finishing loading.
- **SC-002**: From any page in the application, a logged-in user can reach their single most
  relevant destination (cart/orders for Customers, product management for Vendors, shop
  approvals for Administrators) in one click via the navigation bar.
- **SC-003**: Across all four visitor types (guest, Customer, Vendor, Administrator), zero
  instances occur of one visitor type seeing homepage or navigation content restricted to a
  different type, verified by checking each type in turn.
- **SC-004**: A Vendor can determine their shop's current approval status without leaving the
  homepage, in 100% of homepage visits.
- **SC-005**: An Administrator can determine how many shops are awaiting approval without leaving
  the homepage, in 100% of homepage visits.

## Assumptions

- Product highlights shown to guests/Customers are a small, bounded set (e.g., the most recently
  added products), consistent with existing catalog listing behavior — exact count is a planning
  detail, not a scope change.
- "Recent orders" shown to Vendors/Administrators are a small, bounded set (e.g., the 5 most
  recent), not the full order history.
- No new backend endpoints are strictly required; this feature reuses data already exposed by
  existing product, order, vendor-shop, and admin-shop-approval functionality. If a planning-time
  review determines existing endpoints cannot reasonably serve a needed summary (e.g., an
  efficient pending-shop count), a minimal supporting endpoint may be added without changing this
  spec's scope.
- The existing three-role model and shop approval state machine are authoritative and unchanged;
  this feature only adds a presentation layer on top of them.

# Feature Specification: Accounts & Authentication

**Feature Branch**: `001-accounts-auth`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "Accounts & Authentication: user registration, login, logout, and role assignment for the three roles defined in the constitution (Customer, Vendor, Administrator). Customers self-register. Vendors register and additionally submit a shop-creation request that starts PENDING (per the Vendor Approval Gate in the constitution) until an Administrator approves or rejects it. Administrators are not self-registerable — seeded/provisioned separately. Passwords must be hashed per Principle III. Include login/logout, session/token handling (short-lived access token in memory, httpOnly/Secure/SameSite refresh cookie per Principle III), and basic profile fields needed by later features (name, email, role, and for vendors: shop name/status). This is the foundational feature other feature areas (catalog, cart, orders) will depend on for identity and role checks." Extended per follow-up: include password reset / forgot password, email verification, and multiple shops per vendor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customer registers and logs in (Priority: P1)

A new visitor creates a Customer account with their name, email, and password, is signed in
immediately after registering, and can later log out and log back in with the same credentials.

**Why this priority**: Every other feature area (catalog browsing as a known user, cart, orders,
feedback) depends on a working Customer identity. Without this, nothing downstream can be
demonstrated or tested.

**Independent Test**: Can be fully tested by registering a new Customer account through the
registration form, confirming the session starts automatically, logging out, and logging back in
with the same email/password — delivers a working, demonstrable identity system on its own.

**Acceptance Scenarios**:

1. **Given** a visitor with no account, **When** they submit registration with a valid name,
   unique email, and password meeting the password rules, **Then** an account is created with the
   Customer role and they are signed in.
2. **Given** a visitor submits registration with an email already in use, **When** they submit,
   **Then** registration is rejected with a clear "email already registered" message and no new
   account is created.
3. **Given** a logged-in Customer, **When** they log out, **Then** their session ends and
   subsequent requests to Customer-only actions require logging in again.
4. **Given** a registered Customer, **When** they log in with the correct email and password,
   **Then** they are signed in and see their own profile (name, email, role, verification status).
5. **Given** a registered Customer, **When** they log in with an incorrect password, **Then** the
   login is rejected with a generic invalid-credentials message (not revealing which field was
   wrong).

---

### User Story 2 - Vendor registers and requests one or more shops (Priority: P2)

A visitor registers as a Vendor and, as part of registration, submits a shop name to request their
first shop. The shop request starts in PENDING status. The Vendor can log in and see the status of
each of their shops, can request additional shops at any time, and cannot list products, publish a
catalog, or receive orders through a given shop until that specific shop is APPROVED.

**Why this priority**: The Vendor Approval Gate is called out in the constitution as
non-negotiable and is the feature that makes this a multi-vendor marketplace rather than a single
shop. It depends on Customer-style registration/login already working (P1) but adds the
role-specific and approval-specific behavior.

**Independent Test**: Can be fully tested by registering a new Vendor account with a shop name,
confirming that shop's status shows PENDING, requesting a second shop and confirming it gets its
own independent PENDING status, confirming vendor-only catalog actions are blocked per-shop while
PENDING, and confirming the Vendor can still log in/out like any other account — delivers a
demonstrable approval workflow independent of what an Administrator later does with it.

**Acceptance Scenarios**:

1. **Given** a visitor with no account, **When** they register as a Vendor and provide a shop
   name, **Then** an account is created with the Vendor role and an associated shop record with
   status PENDING.
2. **Given** an existing Vendor account, **When** they submit a request to open an additional
   shop with a new, unused shop name, **Then** a second shop record is created for that same
   Vendor with its own independent status, starting at PENDING.
3. **Given** a Vendor with multiple shops in different statuses (e.g. one APPROVED, one PENDING),
   **When** they view their profile, **Then** each shop's name and status is shown independently.
4. **Given** a Vendor shop that is PENDING, **When** the Vendor attempts a vendor-only action
   reserved for approved shops (e.g. creating a catalog listing) on that shop, **Then** the action
   is refused with a message explaining that shop is awaiting approval, regardless of whether the
   Vendor's other shops are approved.
5. **Given** a Vendor registering (or requesting an additional shop) with a shop name already in
   use by another shop, **When** they submit, **Then** the request is rejected with a clear "shop
   name already taken" message.

---

### User Story 3 - Administrator manages accounts and shop approvals (Priority: P3)

An Administrator (provisioned outside of self-registration) logs in and can view pending Vendor
shop requests, approve or reject each one, and view the list of registered accounts and their
roles/status.

**Why this priority**: Approval has no effect until someone can act on it, but the approval queue
itself is only useful once Vendors are actually registering and requesting shops (P2). This story
closes the loop opened by P2.

**Independent Test**: Can be fully tested by provisioning an Administrator account (outside the
self-registration flow), logging in as that Administrator, viewing a list of PENDING shop
requests, approving one and rejecting another, and confirming the affected shops' status changes
accordingly — independently verifiable without needing Customer or catalog features.

**Acceptance Scenarios**:

1. **Given** an Administrator account exists, **When** they log in, **Then** they can view a list
   of all Vendor shop requests filterable by status (PENDING / APPROVED / REJECTED).
2. **Given** a PENDING shop request, **When** the Administrator approves it, **Then** that shop's
   status changes to APPROVED and the owning Vendor immediately gains access to vendor-only
   actions for that shop, without affecting the Vendor's other shops.
3. **Given** a PENDING shop request, **When** the Administrator rejects it, **Then** that shop's
   status changes to REJECTED and it remains blocked from vendor-only actions, with the reason (if
   provided) visible to the Vendor.
4. **Given** no self-registration path exists for the Administrator role, **When** the
   registration form is used, **Then** Administrator is never offered as a selectable role.

---

### User Story 4 - User verifies their email address (Priority: P4)

After registering, a user receives an email containing a verification link. Following the link
marks their account's email as verified. Until verified, the user can still log in and browse, but
is blocked from the actions that most depend on a reachable email address (placing an order as a
Customer; having any shop approved as a Vendor).

**Why this priority**: Trustworthy contact/identity information matters for orders, payments, and
approvals, but it is not required to demonstrate the core registration/login/approval loop, so it
is layered on after P1–P3 are working.

**Independent Test**: Can be fully tested by registering an account, confirming its email shows as
unverified, confirming a verification-dependent action is blocked, following the verification
link, and confirming the action is now allowed and the profile shows the email as verified —
independently testable without needing the full catalog/checkout flow to exist yet (a stand-in
"verification-dependent action" check is sufficient).

**Acceptance Scenarios**:

1. **Given** a newly registered account, **When** registration completes, **Then** a verification
   email is sent to the address provided and the account's email is marked unverified.
2. **Given** an account with an unverified email, **When** the user follows a valid, unexpired
   verification link, **Then** the account's email is marked verified.
3. **Given** an account with an unverified email, **When** the user attempts a verification-gated
   action (Customer: checkout; Vendor: having a shop approved), **Then** the action is refused
   with a message explaining that email verification is required.
4. **Given** an account with an unverified email, **When** the user requests the verification
   email be resent, **Then** a new verification email is sent.
5. **Given** an expired or already-used verification link, **When** the user follows it, **Then**
   they see a clear message that the link is no longer valid and are offered the option to request
   a new one.
6. **Given** an account whose email is already verified, **When** the user follows an old
   verification link again, **Then** they see a friendly "already verified" message rather than an
   error.

---

### User Story 5 - User resets a forgotten password (Priority: P5)

A user who forgot their password requests a reset via their registered email, receives a
time-limited reset link, and sets a new password through it — without needing to remember or enter
the old one.

**Why this priority**: Important for real-world usability and account recovery, but not required
to demonstrate or test the foundational registration/login/approval flows, so it is the last piece
layered onto this feature.

**Independent Test**: Can be fully tested by registering an account, requesting a password reset
for its email, following the reset link, setting a new password, and confirming login succeeds
with the new password and fails with the old one — independently testable end to end.

**Acceptance Scenarios**:

1. **Given** a registered account, **When** the user requests a password reset for its email,
   **Then** a time-limited, single-use reset link is sent to that email.
2. **Given** an email address with no matching account, **When** a password reset is requested for
   it, **Then** the system responds with the same confirmation message as for a registered email
   (no indication of whether the account exists).
3. **Given** a valid, unexpired reset link, **When** the user submits a new password meeting the
   password rules, **Then** the account's password is updated and all of that account's active
   sessions are signed out.
4. **Given** a password reset just completed, **When** the user logs in with the new password,
   **Then** login succeeds; **When** they attempt to log in with the old password, **Then** login
   fails.
5. **Given** an expired or already-used reset link, **When** the user attempts to use it, **Then**
   the reset is refused with a clear message and the option to request a new link.

---

### Edge Cases

- What happens when someone tries to register with an email that only differs by case
  (`User@Example.com` vs `user@example.com`)? Treated as the same email (case-insensitive
  uniqueness).
- What happens when a Vendor's shop request is REJECTED — can they resubmit? Yes, a Vendor may
  submit a new shop request at any time, including after a rejection, and it re-enters PENDING
  status as its own independent shop record.
- What happens when a Vendor has multiple shops with different statuses? Vendor-only actions are
  evaluated per shop (a REJECTED or PENDING shop cannot act even if the Vendor's other shop is
  APPROVED); the profile lists every shop with its own status.
- What happens when a Customer tries to access a Vendor-only or Administrator-only action
  directly? The action is refused server-side regardless of what the client UI shows, with an
  authorization-denied response — consistent with Constitution Principle I.
- What happens when an access token expires mid-session? The client transparently obtains a new
  access token using the refresh token if the refresh token is still valid; if the refresh token
  is also expired or invalid, the user is signed out and asked to log in again.
- What happens when someone logs out on one device — are other devices/sessions affected? Only the
  session tied to the refresh cookie being cleared ends; other active sessions are unaffected
  (per-session logout, not global logout) — except a password reset, which signs out all sessions.
- What happens if the same email attempts to register twice concurrently (race condition)? Only
  one registration succeeds; the second is rejected as a duplicate email.
- What happens when a verification or reset link is used a second time? It is rejected as invalid
  (already-used / expired), with an appropriate message for each case (see User Stories 4 and 5).
- What happens when a password reset is requested repeatedly for the same email in a short period?
  Each request may issue a new link; previously issued unused links for that account become
  invalid once a newer one is issued, so only the most recent link works.

## Requirements *(mandatory)*

### Functional Requirements

**Registration, login, sessions**

- **FR-001**: System MUST allow a visitor to self-register as a Customer with name, email, and
  password.
- **FR-002**: System MUST allow a visitor to self-register as a Vendor with name, email, password,
  and a shop name; this MUST create an associated shop record with status PENDING.
- **FR-003**: System MUST NOT offer Administrator as a self-registration role; Administrator
  accounts are provisioned outside the registration flow (e.g. seeded directly).
- **FR-004**: System MUST enforce unique, case-insensitive email addresses across all accounts
  regardless of role.
- **FR-005**: System MUST enforce unique shop names across all Vendor shops.
- **FR-006**: System MUST hash passwords before persisting them and MUST NOT store or log
  plaintext passwords, consistent with Constitution Principle III.
- **FR-007**: System MUST allow a registered user to log in with email and password and receive an
  authenticated session.
- **FR-008**: System MUST reject login attempts with invalid credentials using a generic message
  that does not reveal whether the email or the password was incorrect.
- **FR-009**: System MUST allow an authenticated user to log out, ending their current session.
- **FR-010**: System MUST issue a short-lived access credential intended for client-memory storage
  and a longer-lived refresh credential intended for httpOnly/Secure/SameSite cookie storage,
  consistent with Constitution Principle III.
- **FR-011**: System MUST allow a client holding a valid refresh credential to obtain a new access
  credential without re-entering a password.
- **FR-012**: System MUST invalidate the refresh credential tied to a session when that session
  logs out.
- **FR-013**: System MUST expose each authenticated user's own profile: name, email,
  email-verification status, role, and for Vendors, the list of their shops each with its own name
  and status.
- **FR-020**: System MUST enforce role checks (Customer / Vendor / Administrator) server-side on
  every request that depends on role, independent of any client-side UI restriction, consistent
  with Constitution Principle I.
- **FR-021**: System MUST enforce a minimum password strength rule (at minimum: a minimum length)
  at registration and at password reset, and reject weaker passwords with a clear message.

**Vendor shops & approval**

- **FR-014**: System MUST record each shop's status as exactly one of PENDING, APPROVED, or
  REJECTED, defaulting to PENDING at creation, consistent with Constitution Principle II.
- **FR-015**: System MUST prevent vendor-only catalog or order-fulfillment actions on a given shop
  unless that specific shop is APPROVED (enforced server-side, not merely hidden in the UI); the
  status of a Vendor's other shops MUST NOT affect this check, consistent with Constitution
  Principles I and II.
- **FR-016**: System MUST allow an Administrator to list shop requests, filterable by status.
- **FR-017**: System MUST allow an Administrator to approve a PENDING shop, changing its status to
  APPROVED and immediately unblocking vendor-only actions for that shop.
- **FR-018**: System MUST allow an Administrator to reject a PENDING shop, changing its status to
  REJECTED, and MAY record a reason visible to the owning Vendor.
- **FR-019**: System MUST allow a Vendor to own more than one shop and to submit additional
  shop-creation requests at any time, including after a prior shop was rejected; each shop
  requested MUST be tracked and MUST progress through the PENDING/APPROVED/REJECTED lifecycle
  independently of the Vendor's other shops.

**Email verification**

- **FR-022**: System MUST send an email containing a verification link/token to the address
  provided at registration.
- **FR-023**: System MUST mark a newly created account's email as unverified and MUST mark it
  verified once the user completes the verification link/token flow.
- **FR-024**: System MUST block verification-gated actions — placing an order as a Customer, and a
  shop being moved to APPROVED for a Vendor — while the owning account's email is unverified, while
  still allowing login and browsing with an unverified email.
- **FR-025**: System MUST allow a user with an unverified email to request the verification email
  be resent.
- **FR-026**: Verification links/tokens MUST expire after a bounded time window and MUST become
  invalid after being successfully used once; using an expired or already-used link MUST produce a
  clear message rather than a silent failure, and following a link for an already-verified account
  MUST show a non-error "already verified" message.

**Password reset**

- **FR-027**: System MUST allow any user to request a password reset by submitting their
  registered email.
- **FR-028**: System MUST respond identically to a password-reset request whether or not the
  submitted email is registered, so as not to reveal account existence.
- **FR-029**: System MUST send a time-limited, single-use reset link/token to the account's email
  when a reset is requested for an email that has a matching account.
- **FR-030**: System MUST allow a user presenting a valid, unexpired reset token to set a new
  password meeting the password strength rule (FR-021), without needing to supply the old
  password.
- **FR-031**: System MUST invalidate all of an account's active sessions/refresh credentials when
  that account's password is reset.
- **FR-032**: Reset tokens MUST expire after a bounded time window, MUST become invalid after a
  single use, and issuing a new reset token for an account MUST invalidate that account's
  previously issued, still-unused reset tokens.

### Key Entities

- **Account**: A person's identity in the system. Attributes: name, email (unique,
  case-insensitive), hashed password, role (Customer, Vendor, or Administrator), email-verified
  flag, created date. Exactly one role per account.
- **Shop**: A Vendor's storefront request/record. Attributes: shop name (unique across all shops),
  owning Vendor account, status (PENDING / APPROVED / REJECTED), status-change reason (optional,
  set on rejection), created date, status-last-changed date. A Vendor account may own multiple
  Shops (zero or more beyond the first created at registration); each Shop's status lifecycle is
  independent of the Vendor's other Shops.
- **Email Verification Token**: A short-lived, single-use token tied to an Account, issued at
  registration (and on resend), used to mark that Account's email verified.
- **Password Reset Token**: A short-lived, single-use token tied to an Account, issued on request,
  used to authorize setting a new password without the old one. A newer token invalidates that
  Account's older, unused tokens.
- **Session (conceptual)**: The authenticated state tying a logged-in user to their access and
  refresh credentials. Not a user-facing entity but implied by login/logout/refresh/reset behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can complete Customer registration and land in a signed-in state in
  under 1 minute.
- **SC-002**: A new visitor can complete Vendor registration including a shop name and land in a
  signed-in, PENDING-shop state in under 2 minutes.
- **SC-003**: 100% of vendor-only actions are refused server-side for shops that are not APPROVED,
  verified by directly attempting those actions while bypassing the UI, for Vendors with a single
  shop and for Vendors with multiple shops in mixed statuses. (Within this feature, verified at the
  permission-check level, since no vendor-only catalog/order action yet exists to call end-to-end;
  full end-to-end verification follows once the Catalog feature is built.)
- **SC-004**: 100% of attempts to log in with a wrong password or unregistered email are rejected
  with a generic, non-revealing error message.
- **SC-005**: An Administrator can review and resolve (approve or reject) a pending shop request in
  under 30 seconds of interaction time once viewing the request.
- **SC-006**: A user's access credential can be silently renewed via the refresh credential
  without requiring re-entry of a password, for as long as the refresh credential remains valid.
- **SC-007**: No plaintext password ever appears in stored data or logs, verified by inspection of
  the persistence layer and log output.
- **SC-008**: A user can verify their email by following the emailed link in one step, without
  needing to log in again or re-enter any credentials.
- **SC-009**: A user who forgets their password can regain account access through the reset flow,
  without contacting support, in under 5 minutes from requesting the reset to logging in again.
- **SC-010**: 100% of password-reset requests for unregistered emails receive the same
  confirmation response as requests for registered emails (no account enumeration).
- **SC-011**: A Vendor can request and track a second (or further) shop, and see its status
  independently of their first shop's status, without any support intervention.

## Assumptions

- "Session/token handling" is implemented as access + refresh credentials per Constitution
  Principle III; the exact lifetime values (e.g. access credential minutes, refresh credential
  days) are a planning-stage decision, not a specification-stage one — this spec only fixes that
  access is short-lived/in-memory and refresh is longer-lived/httpOnly-cookie.
  - Interpreted access credential lifetime default: short enough to limit exposure if leaked
    (typically minutes), refresh credential lifetime default: long enough to avoid frequent
    re-logins (typically days), exact values deferred to planning.
- Email verification and password-reset token lifetimes are likewise a planning-stage decision;
  this spec only fixes that both are time-limited and single-use.
- Actual email delivery (the outbound transport used to send verification and reset emails) MAY be
  stubbed for the MVP per Constitution Principle IV ("Real Core, Mocked Edges"), as long as it is
  built as a swappable service interface rather than hardcoded into business logic.
- Verification-gated actions are interpreted as: Customer checkout/order placement, and a Vendor
  shop being moved to APPROVED. Browsing, login, and viewing one's own profile remain available
  with an unverified email. This interpretation may be revisited in later feature specs (catalog,
  orders) once those areas are specified in detail.
- Shop names remain unique globally (not merely unique per Vendor) even though a Vendor may now own
  multiple shops — this preserves a simple, unambiguous shop-name lookup across the marketplace.
- Administrator accounts are provisioned via a seed/management process outside this spec's UI
  flows (e.g. a management command or initial data fixture) — the exact provisioning mechanism is
  a planning-stage decision.
- Rate limiting / brute-force login protection is a general non-functional security concern
  already covered by Constitution "Security & Non-Functional Requirements" and is not re-specified
  here as a separate functional requirement; the same applies to rate-limiting repeated
  verification/reset email requests.

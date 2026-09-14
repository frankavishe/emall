# Phase 0 Research: Accounts & Authentication

All items from the Technical Context were already fixed by the ratified Constitution (stack,
storage, app boundaries) or have an unambiguous best-practice default for this stack — no
`NEEDS CLARIFICATION` markers remain. This document records the decisions made and why.

## 1. Access/refresh token issuance

**Decision**: Use `djangorestframework-simplejwt` for token issuance and verification, but
override the default response/cookie handling: the **login**, **register**, and **refresh**
endpoints return the access token in the JSON response body (for the frontend to hold in memory)
and set the refresh token **only** as an httpOnly, Secure, SameSite=Lax cookie — never in the JSON
body and never readable by JavaScript.

**Rationale**: `simplejwt` is the de facto standard DRF JWT library, well-maintained, and already
supports short access / long refresh token pairs and refresh rotation/blacklisting out of the box.
Building token issuance from scratch would duplicate well-tested logic (expiry, signature
verification) for no benefit. The cookie-only-for-refresh behavior is not `simplejwt`'s default
(it normally returns both tokens in the body) and requires a thin custom `TokenObtainPairView`
subclass — this is the standard documented pattern for "SPA + httpOnly refresh cookie" with
`simplejwt` and directly satisfies Constitution Principle III.

**Alternatives considered**:
- *Django session auth (cookie-based, no JWT)*: simpler, but the spec/constitution explicitly call
  for a short-lived access credential + httpOnly refresh credential split, which maps directly to
  JWT access/refresh, not classic session auth.
- *`django-rest-knox`*: token-based auth with good logout/revocation support, but no built-in
  access/refresh split — would require building the two-tier expiry model manually, which
  `simplejwt` already provides.
- *Hand-rolled signed tokens (`itsdangerous`/`TimestampSigner`)*: full control, but reinvents
  rotation/blacklisting/expiry that `simplejwt` already solves; rejected as unnecessary complexity
  for an MVP.

**Rotation/blacklisting**: enable `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` so that
logout (FR-012) and password-reset-triggered global session invalidation (FR-031) can be
implemented by blacklisting the refresh token(s) tied to the account, using `simplejwt`'s token
blacklist app (backed by a Postgres table — consistent with "real core" per Principle IV).

## 2. Custom User model with role + case-insensitive email

**Decision**: A custom `User` model (`AUTH_USER_MODEL`) extending `AbstractBaseUser` +
`PermissionsMixin`, with `email` as the unique, case-insensitive `USERNAME_FIELD`, plus a `role`
`CharField` with choices `CUSTOMER` / `VENDOR` / `ADMINISTRATOR`, and an `is_email_verified`
boolean. Case-insensitive uniqueness is enforced by normalizing the email to lowercase in the
model's `save()`/manager `create_user()` before the unique DB constraint applies (rather than
relying on Postgres `citext`, to avoid an extra DB extension dependency for an MVP).

**Rationale**: Django strongly recommends starting any new project with a custom user model
because swapping it later is painful/near-impossible once migrations exist; this project is at
migration zero, so it must be done now. A single `role` field (rather than three separate boolean
flags or Django's group/permission system) directly matches Constitution Principle VI's requirement
that the three-role model be a first-class, unsimplified field — and keeps role checks a single
equality comparison in permission classes.

**Alternatives considered**:
- *Django's built-in `User` + `Group`/`Permission` system for roles*: more "Django-idiomatic" for
  complex permission graphs, but overkill for exactly 3 mutually-exclusive roles; a plain `role`
  field is simpler and matches the spec's "exactly one role per account" (Key Entities: Account).
- *Postgres `citext` extension for case-insensitive email*: cleaner at the DB layer, but adds an
  extension/migration dependency; normalizing on write is simpler for MVP scope and equally correct
  given email is never freeform user-editable text elsewhere.

## 3. Email verification & password reset tokens

**Decision**: Two dedicated Postgres-backed models — `EmailVerificationToken` and
`PasswordResetToken` — each storing a random opaque token (via `secrets.token_urlsafe`), a FK to
`User`, an `expires_at`, and a `used_at` (null until consumed). A token is valid only if
`used_at is None` and `expires_at > now()`. Issuing a new token for the same purpose invalidates
(marks used, or deletes) the account's prior unused tokens of that type, satisfying spec FR-026
and FR-032. Expiry windows: verification links 24 hours, reset links 1 hour (standard industry
defaults for each purpose — verification is low-risk and can be generous, reset is higher-risk and
kept short).

**Rationale**: Storing tokens as DB rows (rather than stateless signed tokens) makes "single-use"
and "invalidate older tokens when a new one issues" trivial and auditable, and keeps this fully in
the "real core" (Constitution Principle IV — auth-adjacent logic is not an external edge to mock).
A random opaque token looked up by DB row is simpler to reason about and equally secure to a signed
JWT-style token for this purpose, and avoids a second token format/library in the codebase beyond
`simplejwt`.

**Alternatives considered**:
- *Django's built-in `PasswordResetTokenGenerator`* (stateless, HMAC-based, used by
  `django.contrib.auth`): reusable for password reset, but doesn't naturally cover email
  verification (different purpose/salt) or the "single reset link at a time" requirement (FR-032)
  without extra state anyway — since state is needed regardless, a uniform DB-token approach for
  both verification and reset was chosen for consistency.
- *`django-rest-passwordreset` / `django-allauth` third-party packages*: would provide this out of
  the box, but pulls in a larger dependency (allauth especially) with more surface area than this
  MVP needs; a ~60-line custom implementation is simple enough to own directly per Constitution's
  YAGNI-except-load-bearing-parts guidance (Principle VI).

## 4. Email delivery (the mocked edge)

**Decision**: Define an `EmailService` interface (`apps/core/email.py`) with a single real
implementation for MVP: Django's console email backend in development (prints emails to the
server console/log) via `EMAIL_BACKEND` set from an environment variable. Verification and
password-reset flows call `EmailService.send_verification_email(user, token)` /
`send_password_reset_email(user, token)` — never construct/send email inline in views.

**Rationale**: Directly implements Constitution Principle IV: outbound email transport may be
stubbed for MVP, but must be a swappable service interface, not hardcoded fake branches in business
logic. Swapping to a real SMTP/SES/Postmark backend later is purely an environment variable change
(`EMAIL_BACKEND`), with zero changes to `accounts`/`vendors` view code.

**Alternatives considered**:
- *Send no email at all, just expose the token via API response for manual testing*: faster to
  wire up, but violates Principle IV's "real, swappable service interface" requirement and would
  require a rewrite later; rejected.
- *Integrate a real transactional email provider now (SendGrid/Postmark)*: real, but requires a
  third-party account/API key before this feature can even be developed — Constitution explicitly
  allows deferring this.

## 5. Per-shop vendor-approval enforcement

**Decision**: `Shop.status` is a `CharField` with choices `PENDING`/`APPROVED`/`REJECTED`
(default `PENDING`), FK `owner` → `User` (no `unique=True` on the FK, since a Vendor may own
multiple Shops), and `name` unique across all shops. A reusable DRF permission class
`IsApprovedShopOwner` (or an object-level check in future catalog/order views) checks
`shop.status == 'APPROVED'` **and** `shop.owner == request.user` for the specific shop object being
acted on — never a blanket "is this user's *any* shop approved" check — so Constitution Principle
II and spec FR-015 (per-shop gating) hold even when a Vendor has shops in mixed statuses.

**Rationale**: Directly matches the spec's Key Entities (Shop is 1:N off Vendor) and FR-014/015/019.
Making status a plain DB field (not computed) keeps the state machine authoritative and inspectable
by an Administrator, and keeps future catalog/order features' authorization check a one-line
comparison against a concrete field, consistent with Constitution's "Extensibility/Reusability"
non-functional requirement (shared logic in reusable service/permission functions, not duplicated
per-view).

**Alternatives considered**:
- *Boolean `is_approved` flag instead of a 3-state enum*: loses the REJECTED state and the ability
  to show a Vendor *why* they're blocked vs. simply "not yet approved" — spec FR-014 and Vendor
  Approval Gate explicitly require the 3-state model.
- *One Shop per Vendor (FK with `unique=True`)*: was the original single-shop assumption; explicitly
  overridden by the user's request to support multiple shops per Vendor, so rejected.

## 6. Testing approach

**Decision**: `pytest` + `pytest-django` for the Django test runner integration, `factory_boy` for
building `User`/`Shop`/token test fixtures, and DRF's `APIClient` for endpoint-level tests that
exercise the real permission classes (so "vendor-only action refused for non-approved shop" is
tested as an actual HTTP 403, not just a unit-level function call) — directly supporting Success
Criteria SC-003 and SC-004 as automatable checks.

**Rationale**: `pytest-django` + `factory_boy` is the standard, widely-documented combination for
Django/DRF projects and integrates cleanly with the Constitution's requirement that every chunk be
"run for real" (migrations + endpoints exercised) before being considered done.

**Alternatives considered**:
- *Django's built-in `TestCase` + `unittest` style*: works fine, but `pytest`'s fixture model and
  assertion introspection are more ergonomic for the iterative, reviewed-chunk workflow this
  project follows; either would satisfy the constitution, `pytest` chosen for developer ergonomics.

## 7. Frontend token handling shape

**Decision**: A React context (`auth-context.tsx`) holds the access token and current user profile
in memory only (component state, not `localStorage`); an `api-client.ts` fetch wrapper attaches the
access token as an `Authorization: Bearer` header, sends `credentials: 'include'` so the httpOnly
refresh cookie rides along automatically, and on a `401` transparently calls the refresh endpoint
once before retrying the original request or, if refresh also fails, clears in-memory state and
redirects to login.

**Rationale**: This is the standard, widely-documented pattern for "SPA holds access token in
memory, refresh token in httpOnly cookie" and is what Constitution Principle III's wording
("short-lived access tokens held in memory on the frontend only") directly specifies.

**Alternatives considered**:
- *Store access token in `localStorage`*: simpler to implement (survives page refresh without a
  silent-refresh call on load) but explicitly disallowed by Principle III (XSS-exfiltration risk);
  rejected outright, not just deprioritized.

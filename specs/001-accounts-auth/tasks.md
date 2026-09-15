---

description: "Task list template for feature implementation"
---

# Tasks: Accounts & Authentication

**Input**: Design documents from `/specs/001-accounts-auth/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md,
data-model.md, contracts/auth-api.md, quickstart.md

**Tests**: Included. `plan.md`'s Technical Context and `research.md` §6 commit this feature to a
`pytest` + `pytest-django` + `factory_boy` + DRF `APIClient` testing approach, and Success Criteria
SC-003/SC-004/SC-010 require server-side enforcement to be verifiable, not just asserted — so
contract tests are written per endpoint, first, before the implementation that makes them pass.

**Organization**: Tasks are grouped by user story (P1–P5 from spec.md) to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Paths follow `plan.md`'s Project Structure: `backend/apps/{core,accounts,vendors}/`,
  `backend/tests/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create Django project skeleton (`manage.py`, `config/settings.py`, `config/urls.py`) at
      `backend/` per plan.md Project Structure
- [x] T002 Create `backend/requirements.txt` with Django 5.x, djangorestframework,
      djangorestframework-simplejwt, django-cors-headers, psycopg2-binary, django-environ,
      pytest, pytest-django, factory_boy
- [x] T003 [P] Configure linting/formatting for backend (ruff or black+isort+flake8) via
      `backend/pyproject.toml`
- [x] T004 Create Next.js (TypeScript, App Router) project skeleton at `frontend/` per plan.md
      Project Structure
- [x] T005 [P] Add `frontend/.env.local.example` documenting `NEXT_PUBLIC_API_BASE_URL`
- [x] T006 [P] Configure linting/formatting for frontend (eslint + prettier) in `frontend/`

**Checkpoint**: Both projects scaffold and boot (`python manage.py runserver`,
`npm run dev`) with no routes yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented —
identity model, token issuance shape, and shared permission/email interfaces every story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create `core`, `accounts`, `vendors` Django app skeletons (`apps.py`, `__init__.py`,
      `migrations/__init__.py`) at `backend/apps/core/`, `backend/apps/accounts/`,
      `backend/apps/vendors/`; register all three in `INSTALLED_APPS` in `backend/config/settings.py`
- [x] T008 Configure PostgreSQL connection and all secrets (`SECRET_KEY`, DB credentials, CORS
      origins, `EMAIL_BACKEND`) from environment variables via django-environ in
      `backend/config/settings.py` (Constitution Principle III: "Secrets ... MUST come from
      environment variables, never committed to the repository"; "Portability": same codebase runs
      in any environment via config)
- [x] T009 [P] Create custom `User` model in `backend/apps/accounts/models.py` extending
      `AbstractBaseUser` + `PermissionsMixin` with fields per data-model.md: `email` (`EmailField`,
      `unique=True`, normalized to lowercase in `save()`), `name` (`CharField`), `role`
      (`CharField` with `choices=[("CUSTOMER", ...), ("VENDOR", ...), ("ADMINISTRATOR", ...)]`,
      no default — must be set explicitly at creation), `is_email_verified` (`BooleanField`,
      `default=False`), `is_active` (`BooleanField`, `default=True`), `date_joined`
      (`DateTimeField(auto_now_add=True)`); set `USERNAME_FIELD = "email"`, no separate `username`
      field
- [x] T010 Create custom `UserManager` in `backend/apps/accounts/models.py` with `create_user()`
      and `create_superuser()` that normalize `email` to lowercase before saving and hash the
      password via `set_password()` (Constitution Principle III: passwords "MUST be hashed (never
      stored/logged in plaintext)")
- [x] T011 Set `AUTH_USER_MODEL = "accounts.User"` in `backend/config/settings.py` (depends on
      T009, must be set before the first migration)
- [x] T012 [P] Generate and apply the initial `accounts` migration (`User` model only) via
      `python manage.py makemigrations accounts && python manage.py migrate` (depends on T009,
      T010, T011)
- [x] T013 [P] Configure `djangorestframework-simplejwt` in `backend/config/settings.py`:
      `SIMPLE_JWT` dict with a short `ACCESS_TOKEN_LIFETIME` and longer `REFRESH_TOKEN_LIFETIME`
      (research.md §1), `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`; add
      `rest_framework_simplejwt.token_blacklist` to `INSTALLED_APPS` and migrate its tables
- [x] T014 Implement a custom token-issuance helper/mixin (not a routed endpoint on its own) in
      `backend/apps/accounts/views.py` (subclassing `TokenObtainPairSerializer`/building on
      `simplejwt`) that returns `{"access": "<jwt>"}` in the response body only and sets the
      refresh token **exclusively** as an httpOnly, Secure, SameSite=Lax cookie — never in the
      JSON body (Constitution Principle III: "short-lived access tokens held in memory on the
      frontend only, refresh tokens set as httpOnly/Secure/SameSite cookies"; research.md §1) —
      reused by the register/login/refresh views built in later phases
- [x] T015 [P] Implement `EmailService` abstract interface plus a console-backend implementation
      in `backend/apps/core/email.py` with `send_verification_email(user, token)` and
      `send_password_reset_email(user, token)` methods, selected via `EMAIL_BACKEND` env var
      (Constitution Principle IV: outbound email transport "MAY be stubbed for the MVP, but MUST
      be implemented as a real, swappable service interface ... rather than hardcoded fake
      branches inlined into business logic")
- [x] T016 [P] Implement reusable DRF permission classes `IsRole(role)` / `IsCustomer` /
      `IsVendor` / `IsAdministrator` in `backend/apps/core/permissions.py`, checking
      `request.user.is_authenticated and request.user.role == <role>` server-side (Constitution
      Principle I: "Role checks MUST be enforced server-side on every request; any client-side
      role check ... MUST NOT be relied upon for authorization")
- [x] T017 Configure `django-cors-headers` in `backend/config/settings.py` to allow the frontend
      origin with `CORS_ALLOW_CREDENTIALS=True` (required for the refresh cookie to be sent
      cross-origin during local dev)
- [x] T018 [P] Scaffold `frontend/src/lib/api-client.ts`: a `fetch` wrapper that attaches
      `Authorization: Bearer <access>` from the auth context, always sends
      `credentials: 'include'`, and on a `401` calls `/api/auth/refresh` once before retrying the
      original request (research.md §7)
- [x] T019 [P] Scaffold `frontend/src/lib/auth-context.tsx`: a React context holding the access
      token and current user profile in memory only (component state, never `localStorage`),
      exposing `login()`, `logout()`, and the current user to the rest of the app (research.md §7,
      Constitution Principle III)

**Checkpoint**: Foundation ready — migrations apply cleanly, `User` model exists with roles, token
issuance shape and shared permission/email interfaces exist. User story implementation can now
begin.

---

## Phase 3: User Story 1 - Customer registers and logs in (Priority: P1) 🎯 MVP

**Goal**: A visitor can self-register as a Customer, land signed in, log out, and log back in;
invalid credentials are rejected with a generic message.

**Independent Test**: Register a new Customer account through `POST /api/auth/register/customer`,
confirm the session starts automatically (`access` token returned, refresh cookie set), log out via
`POST /api/auth/logout`, and log back in via `POST /api/auth/login` with the same email/password.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation

- [x] T020 [P] [US1] Contract test `POST /api/auth/register/customer` — success (201, role
      CUSTOMER, access token + refresh cookie returned), duplicate email (400, spec FR-001 AC2),
      case-insensitive duplicate (`User@x.com` vs `user@x.com`, FR-004), weak password (400,
      FR-021) in `backend/tests/accounts/test_register_customer.py`
- [x] T021 [P] [US1] Contract test `POST /api/auth/login` — success (200), wrong password and
      unregistered email both return the **same generic** 401 message (FR-008, SC-004) in
      `backend/tests/accounts/test_login.py`
- [x] T022 [P] [US1] Contract test `POST /api/auth/logout` — blacklists the current refresh token,
      clears the cookie, a subsequent `refresh` with that cookie fails 401 (FR-009, FR-012) in
      `backend/tests/accounts/test_logout.py`
- [x] T023 [P] [US1] Contract test `POST /api/auth/refresh` — valid refresh cookie yields a new
      access token (FR-011); missing/expired/blacklisted refresh cookie returns 401 (FR-010) in
      `backend/tests/accounts/test_refresh.py`
- [x] T024 [P] [US1] Contract test `GET /api/auth/me` — returns own profile (name, email, role,
      `is_email_verified`) for an authenticated request, 401 unauthenticated (FR-013) in
      `backend/tests/accounts/test_me.py`

### Implementation for User Story 1

- [x] T025 [US1] Implement `RegisterCustomerSerializer` in `backend/apps/accounts/serializers.py`:
      `name`, `email`, `password` fields; validates password strength via Django's password
      validators (FR-021); `role` is hardcoded to `CUSTOMER` server-side, never accepted from the
      client (FR-003)
- [x] T026 [US1] Implement `RegisterCustomerView` in `backend/apps/accounts/views.py`: creates the
      `User` (role=CUSTOMER) inside a DB transaction, issues tokens via T014's token view logic,
      and triggers `EmailService.send_verification_email` (fire-and-forget — failure to send must
      not fail registration) (depends on T009, T014, T015, T025)
- [x] T027 [US1] Implement `LoginView` in `backend/apps/accounts/views.py` built on T014: validates
      email/password, returns the generic invalid-credentials message on failure without revealing
      which field was wrong (FR-008) (depends on T014)
- [x] T028 [US1] Implement `LogoutView` in `backend/apps/accounts/views.py`: blacklists the refresh
      token found in the request cookie via `simplejwt`'s blacklist app, clears the cookie (FR-009,
      FR-012) (depends on T013)
- [x] T029 [US1] Implement `RefreshView` in `backend/apps/accounts/views.py`: reads the refresh
      token from the httpOnly cookie (never the body), issues a new access token, rotates and
      re-sets the refresh cookie (FR-010, FR-011) (depends on T013, T014)
- [x] T030 [US1] Implement `MeView` in `backend/apps/accounts/views.py`: `GET` returns the
      authenticated user's own `name`, `email`, `role`, `is_email_verified` (FR-013) (depends on
      T009)
- [x] T031 [US1] Wire `backend/apps/accounts/urls.py` (`register/customer`, `login`, `logout`,
      `refresh`, `me`) and include it under `/api/auth/` in `backend/config/urls.py` (depends on
      T025–T030)
- [x] T032 [P] [US1] Build `frontend/src/app/register/page.tsx` (Customer variant): form for name,
      email, password; on success stores the access token via `auth-context` and redirects to
      `/account`
- [x] T033 [P] [US1] Build `frontend/src/app/login/page.tsx`: form for email/password; on success
      stores the access token via `auth-context`; on failure shows the generic error message
      returned by the API
- [x] T034 [US1] Build `frontend/src/app/account/page.tsx`: calls `GET /api/auth/me` on load via
      `api-client`, displays name/email/role/verification status, and a logout button calling
      `POST /api/auth/logout` then clearing `auth-context` (depends on T018, T019, T032, T033)

**Checkpoint**: User Story 1 is fully functional and independently testable — Customer
registration, login, logout, refresh all work end to end against real Postgres.

---

## Phase 4: User Story 2 - Vendor registers and requests one or more shops (Priority: P2)

**Goal**: A visitor can self-register as a Vendor with an initial shop (PENDING), request
additional shops later, and see every shop's status independently; vendor-only actions are blocked
per-shop while not APPROVED. **Verification note**: since no vendor-only catalog/order endpoint
exists yet in this feature, the per-shop gate is verified at the permission-class level (T038)
rather than via a live HTTP action; full end-to-end verification follows once Catalog is built.

**Independent Test**: Register a Vendor via `POST /api/auth/register/vendor` with a shop name,
confirm that shop is PENDING; `POST /api/vendor/shops` a second shop with a different name and
confirm it is independently PENDING; confirm a vendor-only action is refused on a PENDING shop
regardless of the other shop's status.

### Tests for User Story 2 ⚠️

- [ ] T035 [P] [US2] Contract test `POST /api/auth/register/vendor` — success creates `User`
      (role=VENDOR) + one `Shop` (status=PENDING) (FR-002), duplicate email (400), duplicate shop
      name (400, User Story 2 AC5), weak password (400) in
      `backend/tests/accounts/test_register_vendor.py`
- [ ] T036 [P] [US2] Contract test `GET /api/vendor/shops` — returns only the authenticated
      Vendor's own shops, filtered at the queryset level by `owner=request.user` (Constitution
      "Security" NFR), 403 for non-Vendor roles in `backend/tests/vendors/test_list_shops.py`
- [ ] T037 [P] [US2] Contract test `POST /api/vendor/shops` — creates an additional PENDING shop
      for an existing Vendor (FR-019), rejects a duplicate shop name (400, FR-005) in
      `backend/tests/vendors/test_create_shop.py`
- [ ] T038 [P] [US2] Unit test `IsApprovedShopOwner.has_object_permission()` (FR-015, depends on
      T044): given a Vendor with one APPROVED and one PENDING shop, permission returns `True` for
      the APPROVED shop and `False` for the PENDING shop (same Vendor), and `False` for either
      shop when requested by a different Vendor or a non-Vendor role — called directly against
      `Shop` instances and factory `request.user` objects, without requiring an HTTP endpoint (no
      vendor-only catalog/order action exists yet in this feature's scope; that will be exercised
      end-to-end once the Catalog feature is built) in `backend/tests/vendors/test_shop_gating.py`

### Implementation for User Story 2

- [ ] T039 [US2] Create `Shop` model in `backend/apps/vendors/models.py` per data-model.md:
      `owner` (`ForeignKey(User, on_delete=CASCADE, related_name="shops")`, **not** unique — a
      Vendor may own multiple shops), `name` (`CharField`, `unique=True` across all shops),
      `status` (`CharField`, `choices=[("PENDING", ...), ("APPROVED", ...), ("REJECTED", ...)]`,
      `default="PENDING"`), `status_reason` (`TextField`, `null=True`, `blank=True`), `created_at`
      (`DateTimeField(auto_now_add=True)`), `status_changed_at` (`DateTimeField`, `null=True`,
      updated whenever `status` changes)
- [ ] T040 [P] [US2] Generate and apply the initial `vendors` migration (`Shop` model) (depends on
      T039)
- [ ] T041 [US2] Implement `RegisterVendorSerializer` in `backend/apps/accounts/serializers.py`:
      `name`, `email`, `password`, `shop_name`; validates password strength via Django's password
      validators (FR-021, same rule as T025); `role` hardcoded to `VENDOR` server-side (FR-003)
- [ ] T042 [US2] Implement `RegisterVendorView` in `backend/apps/accounts/views.py`: creates the
      `User` (role=VENDOR) and its first `Shop` (status=PENDING) in one DB transaction
      (Constitution "Reliability"), issues tokens, triggers verification email (depends on T039,
      T041)
- [ ] T043 [US2] Implement `ShopSerializer` and `VendorShopListCreateView` in
      `backend/apps/vendors/views.py`, restricted to `IsVendor` (T016): `GET` lists shops filtered
      to `owner=request.user`; `POST` creates a new shop (status defaults to PENDING) for the
      authenticated Vendor (FR-019, FR-020) (depends on T016, T039)
- [ ] T044 [US2] Implement `IsApprovedShopOwner` permission in `backend/apps/vendors/permissions.py`
      that checks `shop.status == "APPROVED"` **and** `shop.owner == request.user` for the specific
      shop object being acted on — never account-wide (FR-015, research.md §5)
- [ ] T045 [US2] Wire `backend/apps/vendors/urls.py` (`/api/vendor/shops`) and include it in
      `backend/config/urls.py` (depends on T043)
- [ ] T046 [US2] Extend `MeView` (`backend/apps/accounts/views.py`) to include a `shops` array
      (`id`, `name`, `status`) when `role == "VENDOR"` (FR-013) (depends on T030, T039)
- [ ] T047 [P] [US2] Extend `frontend/src/app/register/page.tsx` with a Vendor variant (adds
      `shop_name` field, posts to `register/vendor`) (depends on T032)
- [ ] T048 [US2] Extend `frontend/src/app/account/page.tsx` to list every shop and its status for
      Vendors, plus a "request another shop" action calling `POST /api/vendor/shops` (depends on
      T034, T046)

**Checkpoint**: User Stories 1 AND 2 both work independently — Vendors can register, hold multiple
shops, and each shop's approval gate is enforced per-shop.

---

## Phase 5: User Story 3 - Administrator manages accounts and shop approvals (Priority: P3)

**Goal**: An Administrator can list pending shop requests, approve or reject them, and no
Administrator account can ever be created through self-registration.

**Independent Test**: Log in as a seeded Administrator, `GET /api/admin/shops?status=PENDING`,
approve one shop and reject another with a reason, and confirm each affected shop's status updates
independently of the Vendor's other shops.

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Contract test `GET /api/admin/shops?status=PENDING` — paginated (Constitution
      "Resource Utilization"), filterable by status, 403 for non-Administrator roles (FR-016) in
      `backend/tests/vendors/test_admin_list_shops.py`
- [ ] T050 [P] [US3] Contract test `POST /api/admin/shops/{id}/approve` — PENDING→APPROVED (200),
      rejects (400/409) if the shop is not currently PENDING, 403 for non-Administrator (FR-017)
      in `backend/tests/vendors/test_admin_approve.py`
- [ ] T051 [P] [US3] Contract test `POST /api/admin/shops/{id}/reject` — PENDING→REJECTED with an
      optional `reason` persisted and visible to the owning Vendor (FR-018) in
      `backend/tests/vendors/test_admin_reject.py`
- [ ] T052 [P] [US3] Contract test: `register/customer` and `register/vendor` never accept or
      expose a way to set `role=ADMINISTRATOR` (FR-003, spec User Story 3 AC4) in
      `backend/tests/accounts/test_no_admin_self_register.py`

### Implementation for User Story 3

- [ ] T053 [US3] Implement `AdminShopListSerializer` (includes owner name/email) and
      `AdminShopListView` in `backend/apps/vendors/views.py`: paginated, filterable by `?status=`
      query param, restricted to `IsAdministrator` (T016) (depends on T016, T039)
- [ ] T054 [US3] Implement `AdminShopApproveView` in `backend/apps/vendors/views.py`: transitions a
      PENDING shop to APPROVED inside a DB transaction, sets `status_changed_at`, rejects the
      transition from any other status (depends on T016, T039)
- [ ] T055 [US3] Implement `AdminShopRejectView` in `backend/apps/vendors/views.py`: transitions a
      PENDING shop to REJECTED inside a DB transaction, stores the optional `reason` in
      `status_reason`, sets `status_changed_at` (depends on T016, T039)
- [ ] T056 [US3] Wire admin shop URLs (`/api/admin/shops`, `/api/admin/shops/{id}/approve`,
      `/api/admin/shops/{id}/reject`) in `backend/apps/vendors/urls.py` (depends on T053–T055)
- [ ] T057 [US3] Add a `seed_admin` Django management command in
      `backend/apps/accounts/management/commands/seed_admin.py` that creates a `User`
      (role=ADMINISTRATOR) from env-provided credentials, per spec Assumptions ("Administrator
      accounts are provisioned via a seed/management process outside this spec's UI flows")
- [ ] T058 [P] [US3] Build `frontend/src/app/admin/shops/page.tsx`: lists shops filterable by
      status, with approve/reject actions calling the admin endpoints (depends on T018, T019)

**Checkpoint**: All three core roles now work independently — Customer, Vendor (multi-shop), and
Administrator approval.

---

## Phase 6: User Story 4 - User verifies their email address (Priority: P4)

**Goal**: A newly registered account starts unverified; following the emailed link verifies it;
verification-gated actions are blocked until then. **Scope note**: FR-024 names two gated actions
— Customer checkout and Vendor shop approval. Only the shop-approval half (T068/T069) is
implemented/tested here, since Customer checkout doesn't exist until the future Orders/Checkout
feature; that half of FR-024 will be wired up there.

**Independent Test**: Register an account, confirm `is_email_verified` is `false`, confirm a
verification-gated action is refused, follow the (console-logged) verification link, confirm
`is_email_verified` becomes `true` and the action is now allowed.

### Tests for User Story 4 ⚠️

- [ ] T059 [P] [US4] Contract test `POST /api/auth/verify-email/confirm` — valid unexpired token
      verifies the account (200, FR-023); expired or already-used token returns 400 with a clear
      message (FR-026, spec User Story 4 AC5); an already-verified account following an old link
      gets a non-error "already verified" message (AC6) in
      `backend/tests/accounts/test_verify_email_confirm.py`
- [ ] T060 [P] [US4] Contract test `POST /api/auth/verify-email/request` — issues a new token and
      invalidates the account's prior unused verification tokens, so only the newest link works
      (FR-025, FR-026) in `backend/tests/accounts/test_verify_email_request.py`
- [ ] T061 [P] [US4] Test verification-gated action (shop approval eligibility) is refused while
      the owning Vendor's email is unverified, and succeeds once verified (FR-024) in
      `backend/tests/accounts/test_verification_gate.py`

### Implementation for User Story 4

- [ ] T062 [US4] Create `EmailVerificationToken` model in `backend/apps/accounts/models.py` per
      data-model.md: `user` (`ForeignKey(User, on_delete=CASCADE, related_name="email_verification_tokens")`),
      `token` (`CharField`, `unique=True`, indexed, generated via `secrets.token_urlsafe(32)`),
      `created_at` (`DateTimeField(auto_now_add=True)`), `expires_at` (`DateTimeField`, set to
      `created_at + 24h` per research.md §3), `used_at` (`DateTimeField`, `null=True`) — valid iff
      `used_at is None and expires_at > now()`
- [ ] T063 [P] [US4] Generate and apply the migration adding `EmailVerificationToken` (depends on
      T062)
- [ ] T064 [US4] Implement `issue_verification_token(user)` in `backend/apps/accounts/services.py`:
      marks the user's other unused `EmailVerificationToken` rows used, creates and returns a new
      one, and calls `EmailService.send_verification_email` (T015) (depends on T015, T062)
- [ ] T065 [US4] Implement `VerifyEmailRequestView` in `backend/apps/accounts/views.py`
      (authenticated) calling T064 (FR-025) (depends on T064)
- [ ] T066 [US4] Implement `VerifyEmailConfirmView` in `backend/apps/accounts/views.py`
      (unauthenticated, token is the credential): validates the token per T062's validity rule,
      sets `used_at` and `user.is_email_verified=True`; returns "already verified" (not an error)
      if the account is already verified; returns 400 for invalid/expired/used tokens (FR-023,
      FR-026) (depends on T062)
- [ ] T067 [US4] Wire `verify-email/request` and `verify-email/confirm` in
      `backend/apps/accounts/urls.py` (depends on T065, T066)
- [ ] T068 [US4] Implement a reusable `require_verified_email(user)` check in
      `backend/apps/core/permissions.py`, raising a permission-denied response when
      `not user.is_email_verified` (FR-024), for reuse by this feature and future
      catalog/checkout features
- [ ] T069 [US4] Apply T068's check inside `AdminShopApproveView` (T054) so a shop cannot be moved
      to APPROVED while its owning Vendor's email is unverified (FR-024) (depends on T054, T068)
- [ ] T070 [P] [US4] Build `frontend/src/app/verify-email/page.tsx`: reads `token` from the URL
      query string, calls `verify-email/confirm`, shows the result, and offers a "resend" action
      calling `verify-email/request` when appropriate

**Checkpoint**: Registration → verification loop works end to end and gates the actions specified
in FR-024.

---

## Phase 7: User Story 5 - User resets a forgotten password (Priority: P5)

**Goal**: A user can request a password reset by email, receive a time-limited single-use link,
and set a new password — invalidating all of that account's active sessions.

**Independent Test**: Request a reset for a registered email, follow the (console-logged) reset
link, set a new password, confirm login succeeds with the new password and fails with the old one,
and confirm a pre-reset refresh cookie no longer works.

### Tests for User Story 5 ⚠️

- [ ] T071 [P] [US5] Contract test `POST /api/auth/password-reset/request` — registered and
      unregistered emails receive the **identical** 202 response (FR-028, SC-010) in
      `backend/tests/accounts/test_password_reset_request.py`
- [ ] T072 [P] [US5] Contract test `POST /api/auth/password-reset/confirm` — valid token sets the
      new password and blacklists all of the account's outstanding refresh tokens (FR-030,
      FR-031); expired/already-used token returns 400 (FR-032); weak new password returns 400
      (FR-021) in `backend/tests/accounts/test_password_reset_confirm.py`

### Implementation for User Story 5

- [ ] T073 [US5] Create `PasswordResetToken` model in `backend/apps/accounts/models.py` per
      data-model.md: same shape as `EmailVerificationToken` (T062) but `related_name=
      "password_reset_tokens"` and `expires_at = created_at + 1h` per research.md §3 (shorter than
      verification — higher-risk action)
- [ ] T074 [P] [US5] Generate and apply the migration adding `PasswordResetToken` (depends on T073)
- [ ] T075 [US5] Implement `PasswordResetRequestView` in `backend/apps/accounts/views.py`
      (unauthenticated): always returns the same 202 response regardless of whether the email
      matches an account; when it does, invalidates the account's prior unused reset tokens, issues
      a new one, and calls `EmailService.send_password_reset_email` (T015) (FR-027, FR-028, FR-029,
      FR-032) (depends on T015, T073)
- [ ] T076 [US5] Implement `PasswordResetConfirmView` in `backend/apps/accounts/views.py`
      (unauthenticated, token is the credential): inside one DB transaction — validates the token
      per T073's validity rule, validates the new password's strength (FR-021), sets the new
      hashed password, marks the token used, and blacklists every outstanding refresh token for
      that user via `simplejwt`'s blacklist app (FR-030, FR-031) (depends on T013, T073)
- [ ] T077 [US5] Wire `password-reset/request` and `password-reset/confirm` in
      `backend/apps/accounts/urls.py` (depends on T075, T076)
- [ ] T078 [P] [US5] Build `frontend/src/app/forgot-password/page.tsx`: submits an email, always
      shows the same generic confirmation message
- [ ] T079 [P] [US5] Build `frontend/src/app/reset-password/page.tsx`: reads `token` from the URL
      query string, submits a new password, redirects to `/login` on success

**Checkpoint**: All five user stories are independently functional — the full Accounts &
Authentication feature works end to end.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T080 [P] Confirm `AdminShopListView` (T053) pagination is active and default page size is
      sane, per Constitution "Resource Utilization" ("list endpoints MUST be paginated") in
      `backend/apps/vendors/views.py`
- [ ] T081 [P] Add DRF throttle classes to `login`, `password-reset/request`, and
      `verify-email/request` in `backend/config/settings.py` / relevant views, to bound
      brute-force/spam attempts (Constitution "Security & Non-Functional Requirements")
- [ ] T082 Run all five `quickstart.md` scenarios end to end against a real PostgreSQL database
      with migrations applied, per Constitution Principle V ("verified as actually working —
      migrations run, API exercised ... before moving to the next chunk")
- [ ] T083 [P] Write `backend/README.md` (or extend `docs/`) with setup/run instructions for this
      feature: env vars required, `migrate`, `seed_admin`, `runserver`, `npm run dev`
- [ ] T084 Security review pass: confirm no plaintext password ever appears in the database or in
      server logs (SC-007); confirm all secrets are sourced from environment variables, none
      committed (Constitution Principle III)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (User model,
  token issuance shape, and shared permission/email interfaces are used by every story)
- **User Stories (Phase 3–7)**: All depend on Foundational phase completion
  - US1 (P1) has no dependency on other stories
  - US2 (P2) depends on US1's registration/token machinery existing (reuses T014's token issuance)
    but is independently testable once built
  - US3 (P3) depends on US2's `Shop` model (T039) existing
  - US4 (P4) depends on US1's `User`/registration (T009, T025/T041) and, for FR-024's shop-approval
    gate, on US3's `AdminShopApproveView` (T054)
  - US5 (P5) depends on US1's `User`/login/token machinery (T009, T013, T014)
  - In practice: implement in priority order **US1 → US2 → US3 → US4 → US5** — each is still an
    independently testable increment per its own Independent Test above
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and failing before implementation
- Models before serializers/views
- Views before URL wiring
- Backend endpoint before its corresponding frontend page
- Story's backend fully working before its frontend is wired to it

### Parallel Opportunities

- All Setup tasks marked [P] (T003, T005, T006) can run in parallel
- Within Foundational: T009 must precede T010–T014; T015, T016, T018, T019 are independent of each
  other and of T013/T014 and can run in parallel once T007/T008 land
- All contract tests within a story (marked [P]) can run in parallel with each other
- Frontend page tasks marked [P] can run in parallel with backend tasks in the same story once the
  endpoint they call exists
- Different user stories' backend work can proceed in parallel across developers once Foundational
  is done, respecting the cross-story dependencies noted above (US3 needs US2's `Shop` model; US4's
  gate task T069 needs US3's T054)

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test POST /api/auth/register/customer in backend/tests/accounts/test_register_customer.py"
Task: "Contract test POST /api/auth/login in backend/tests/accounts/test_login.py"
Task: "Contract test POST /api/auth/logout in backend/tests/accounts/test_logout.py"
Task: "Contract test POST /api/auth/refresh in backend/tests/accounts/test_refresh.py"
Task: "Contract test GET /api/auth/me in backend/tests/accounts/test_me.py"

# Launch the two independent frontend pages together:
Task: "Build frontend/src/app/register/page.tsx (Customer variant)"
Task: "Build frontend/src/app/login/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 independently
5. Demo: Customer can register, log in, log out, log back in

### Incremental Delivery

1. Setup + Foundational → identity foundation ready
2. US1 → validate (quickstart Scenario 1) → demo (Customer auth MVP)
3. US2 → validate (Scenario 2) → demo (Vendor + multi-shop requests)
4. US3 → validate (Scenario 3) → demo (Admin approval loop closes)
5. US4 → validate (Scenario 4) → demo (email verification gate)
6. US5 → validate (Scenario 5) → demo (password reset)
7. Phase 8 polish → final review against Constitution before considering the feature done

### Constitution alignment (Principle V: Spec-Driven, Staged Delivery)

Per the Constitution, implementation MUST proceed in reviewable chunks — **one phase at a time**,
each run for real (migrations applied, endpoints exercised via the DRF browsable API or the actual
Next.js dev server) and reviewed before starting the next. Do not run `/speckit-implement` to
generate all 84 tasks unattended; implement and check off one phase (ideally one user story) at a
time.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability back to spec.md
- Each user story is independently completable and testable per its Independent Test statement
- Verify contract tests fail before implementing the view/serializer that makes them pass
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
- Total: 84 tasks (T001–T084) across Setup (6), Foundational (13), US1 (15), US2 (14), US3 (10),
  US4 (12), US5 (9), Polish (5)

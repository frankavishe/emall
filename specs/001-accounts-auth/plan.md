# Implementation Plan: Accounts & Authentication

**Branch**: `001-accounts-auth` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-accounts-auth/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Build the foundational identity system for the marketplace: Customer and Vendor self-registration,
login/logout with short-lived access + httpOnly-cookie refresh credentials, email verification,
password reset, and a Vendor shop-approval workflow where a Vendor may own multiple shops, each
independently gated PENDING → APPROVED/REJECTED by an Administrator. Implemented as a Django +
Django REST Framework backend (custom `User` model with a `role` field, a `vendors` app owning the
`Shop` model) against PostgreSQL, consumed by a Next.js frontend that holds the access token in
memory and never touches the refresh cookie directly. Email delivery (verification/reset) is a
swappable service interface, real in shape but backed by Django's console email backend for local
dev, per Constitution Principle IV.

## Technical Context

**Language/Version**: Python 3.12 (backend, Django 5.x), TypeScript 5.x / Node 20.x (frontend,
Next.js 14+ App Router)

**Primary Dependencies**: Django, Django REST Framework, `djangorestframework-simplejwt` (access +
refresh token issuance/rotation, customized to deliver the refresh token only via an
httpOnly/Secure/SameSite cookie rather than in the response body), `django-cors-headers` (frontend
origin during local dev), React 18 + Next.js for the frontend, a thin `fetch`-based API client
with an in-memory access-token store (React context) on the frontend.

**Storage**: PostgreSQL (all accounts/shops/tokens — this is the "real core" the Constitution
requires to be fully real, not mocked)

**Testing**: `pytest` + `pytest-django` + `factory_boy` for backend unit/integration tests, DRF's
`APIClient` for endpoint-level contract tests; frontend covered by manual quickstart walkthroughs
at this stage (component-level frontend testing deferred to a later feature unless a bug surfaces
here).

**Target Platform**: Linux server (Django/Gunicorn behind a reverse proxy, containerizable later),
any modern browser (Next.js frontend)

**Project Type**: Web application (separate `backend/` and `frontend/` projects, per the
Constitution's confirmed Django + Next.js stack)

**Performance Goals**: No feature-specific throughput target beyond standard interactive web-app
expectations (auth endpoints responding well under 1s under local/dev load); this feature is not
performance-critical at MVP scale.

**Constraints**: Server-side role/ownership enforcement on every request (Constitution Principle
I); Vendor-only actions gated per-shop, not per-account (Constitution Principle II, spec FR-015);
no raw password or payment data ever logged/persisted in plaintext (Principle III); access token
never persisted to `localStorage`/`sessionStorage`/a non-httpOnly cookie; state-changing operations
(shop approve/reject, password reset) wrapped in DB transactions (Constitution "Reliability").

**Scale/Scope**: Learning-project MVP scale (expected dozens of test accounts/shops during
development, not a production load target); schema and auth design should not preclude scaling
later, but no specific scale target is being engineered for now.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Role Separation & Least Privilege | Every role-dependent endpoint enforces the check server-side via DRF permission classes, not just frontend route guards | **PASS** — plan uses a custom `IsRole`/`IsShopOwner`-style DRF permission layer for every protected view; no client-only checks are treated as authorization |
| II. Vendor Approval Gate (NON-NEGOTIABLE) | Shop has explicit PENDING/APPROVED/REJECTED status, settable only by Administrator, enforced in the same server-side layer | **PASS** — `Shop.status` is a DB-level choice field; only an Administrator-only endpoint can transition it; vendor-only catalog/order actions (future features) will check `shop.status == APPROVED` server-side, per shop |
| III. Data & Payment Security | Passwords hashed; access token in-memory only; refresh token httpOnly/Secure/SameSite; secrets from env vars | **PASS** — Django's default PBKDF2 password hasher; `djangorestframework-simplejwt` access token returned in response body only (frontend keeps it in memory, never persisted); refresh token set via custom httpOnly/Secure/SameSite cookie, never exposed to JS; `SECRET_KEY`/DB creds/email config from environment variables |
| IV. Real Core, Mocked Edges | DB schema/migrations, auth, permission enforcement, and (later) cart→checkout are fully real; only true externals may be stubbed | **PASS** — Postgres schema, auth, and permissions are fully implemented now; only outbound email transport is stubbed (Django console backend for dev), behind an `EmailService` interface so swapping to real SMTP/SES later is a settings change, not a rewrite |
| V. Spec-Driven, Staged Delivery | This plan proceeds to `/speckit-tasks` next, implementation happens in reviewable chunks | **PASS** — plan defers implementation entirely to `/speckit-implement` after `/speckit-tasks`; no code is written in this phase |
| VI. Simplicity Within a Load-Bearing Domain Model | Three-role model and shop approval state machine must not be simplified away | **PASS** — `User.role` enum (Customer/Vendor/Administrator) and `Shop.status` state machine are first-class DB fields, not derived/inferred at runtime; per-line-item order fulfillment is out of scope for this feature (belongs to a future Orders feature) and nothing here precludes it |

No violations requiring justification — Complexity Tracking below is empty.

**Post-Phase-1 re-check**: `research.md` and `data-model.md` decisions (simplejwt with
cookie-only refresh, per-shop status enforcement, DB-backed single-use verification/reset tokens,
`EmailService` interface) were made specifically to satisfy the gates above, not around them — all
six gates still **PASS** after design.

## Project Structure

### Documentation (this feature)

```text
specs/001-accounts-auth/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── auth-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── manage.py
├── config/                     # Django project settings/urls (env-driven per Constitution)
│   ├── settings.py
│   └── urls.py
├── apps/
│   ├── core/                   # Shared cross-app pieces (per Constitution "Maintainability")
│   │   ├── permissions.py      # IsRole / IsShopOwner-style DRF permission classes
│   │   └── email.py            # EmailService interface + console-backend impl (Principle IV)
│   ├── accounts/                # THIS FEATURE: User model, registration, login, tokens
│   │   ├── models.py            # User (role, email-verified flag), EmailVerificationToken,
│   │   │                        # PasswordResetToken
│   │   ├── serializers.py
│   │   ├── views.py             # register, login, logout, refresh, me, verify-email,
│   │   │                        # password-reset request/confirm
│   │   ├── urls.py
│   │   └── permissions.py
│   ├── vendors/                  # THIS FEATURE: Shop model + approval workflow
│   │   ├── models.py             # Shop (FK to User, status, reason)
│   │   ├── serializers.py
│   │   ├── views.py              # vendor: list/create own shops; admin: list/approve/reject
│   │   ├── urls.py
│   │   └── permissions.py
│   ├── catalog/                  # future feature (not touched here)
│   ├── cart/                     # future feature (not touched here)
│   ├── orders/                   # future feature (not touched here)
│   ├── payments/                 # future feature (not touched here)
│   └── feedback/                 # future feature (not touched here)
└── tests/
    ├── accounts/                 # registration/login/logout/refresh/verify/reset tests
    └── vendors/                  # shop creation + approval workflow tests

frontend/
├── src/
│   ├── app/
│   │   ├── register/            # customer + vendor registration pages
│   │   ├── login/
│   │   ├── verify-email/
│   │   ├── forgot-password/
│   │   ├── reset-password/
│   │   └── account/             # profile page showing role + shop(s) status
│   ├── lib/
│   │   ├── auth-context.tsx     # in-memory access token store + refresh-on-401 logic
│   │   └── api-client.ts        # fetch wrapper, credentials: 'include' for refresh cookie
│   └── components/
└── tests/
```

**Structure Decision**: Option 2 (web application: separate `backend/` Django project and
`frontend/` Next.js project), matching the Constitution's confirmed stack and Django app
boundaries. This feature lives primarily in the new `backend/apps/accounts` and
`backend/apps/vendors` apps plus shared pieces in `backend/apps/core`, and the
`frontend/src/app/{register,login,verify-email,forgot-password,reset-password,account}` routes.
Other Django apps listed (`catalog`, `cart`, `orders`, `payments`, `feedback`) are named here only
to establish the app-boundary convention from the Constitution; none of them are created or
modified by this feature.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _None — no Constitution gate violations were identified for this feature._ | — | — |

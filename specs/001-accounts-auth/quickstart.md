# Quickstart: Validating Accounts & Authentication

This is a manual/scripted validation guide, not implementation code. Run it after
`/speckit-implement` has built this feature's tasks, to confirm the feature actually works end to
end per the Constitution's "run for real" requirement — not just that tests pass in isolation.

## Prerequisites

- PostgreSQL running locally (or via `docker compose`, however the project's dev setup lands), a
  database created, and `backend/.env` (or equivalent) pointing at it — no secrets committed
  (Constitution Principle III / "Portability").
- `backend/`: Python 3.12 venv with project dependencies installed (`pip install -r
  requirements.txt` or equivalent).
- `frontend/`: Node 20.x, dependencies installed (`npm install`).

## Setup

```powershell
# From backend/
python manage.py migrate
python manage.py createsuperuser   # or a dedicated management command that seeds an
                                    # ADMINISTRATOR-role User directly, per spec Assumptions
python manage.py runserver
```

```powershell
# From frontend/, in a separate terminal
npm run dev
```

Confirm the backend is reachable (e.g. `GET http://localhost:8000/api/auth/me` returns `401`, not
a connection error) and the frontend loads at `http://localhost:3000`.

## Scenario 1 — Customer registers and logs in (User Story 1 / P1)

1. Via the frontend `/register` page (or `POST /api/auth/register/customer` directly): register
   with a new name/email/password.
   - **Expect**: signed in immediately, `GET /api/auth/me` shows `role: "CUSTOMER"`,
     `is_email_verified: false`.
2. Repeat registration with the same email (any casing).
   - **Expect**: `400`, duplicate-email error, no second account created.
3. Log out, then log back in with the same credentials.
   - **Expect**: `logout` returns `204`; a post-logout call to a protected endpoint with the old
     access token still works until it naturally expires (access tokens aren't revoked on logout,
     only the refresh token is — expected per the access/refresh design), but attempting `refresh`
     after logout fails `401`; fresh `login` succeeds and returns a new access token.
4. Log in with a wrong password.
   - **Expect**: `401` with a generic message, not revealing which field was wrong.

## Scenario 2 — Vendor registers and requests multiple shops (User Story 2 / P2)

1. Register as a Vendor with a shop name via `/register` (vendor variant) or
   `POST /api/auth/register/vendor`.
   - **Expect**: `GET /api/auth/me` shows `role: "VENDOR"`, one shop with `status: "PENDING"`.
2. `POST /api/vendor/shops` with a second, different shop name.
   - **Expect**: `201`, a second shop for the same Vendor, also `status: "PENDING"`, independent
     of the first.
3. Attempt a vendor-only action gated by shop approval (until catalog exists, this can be
   validated with a lightweight stand-in check in the vendor shop serializer/permission tests —
   see `tasks.md` for the exact test) on the PENDING shop.
   - **Expect**: refused, explaining the shop is awaiting approval.
4. Re-register a shop name that already exists (either vendor's).
   - **Expect**: `400` duplicate shop name.

## Scenario 3 — Administrator approves/rejects shops (User Story 3 / P3)

1. Log in as the seeded Administrator account.
2. `GET /api/admin/shops?status=PENDING`.
   - **Expect**: both shops from Scenario 2 listed.
3. `POST /api/admin/shops/{id}/approve` on the first shop.
   - **Expect**: `200`, `status: "APPROVED"`; re-checking the Vendor's `/me` shows that shop
     APPROVED and the other still PENDING (independent per-shop status — spec AC3).
4. `POST /api/admin/shops/{id}/reject` on the second shop with a reason.
   - **Expect**: `200`, `status: "REJECTED"`, reason visible via the Vendor's `/me`/shops list.
5. Attempt to register a new account with `role: "ADMINISTRATOR"` via the public registration
   endpoints.
   - **Expect**: not possible — no such option exists on `register/customer` or `register/vendor`.

## Scenario 4 — Email verification (User Story 4 / P4)

1. Register a new Customer (console email backend will print the verification email/link to the
   backend server log/console — this is the mocked edge per Constitution Principle IV).
2. Copy the token from the console output, `POST /api/auth/verify-email/confirm` with it.
   - **Expect**: `200`, `is_email_verified` now `true` on `/me`.
3. Before verifying (a second, fresh registration), attempt a verification-gated action (checkout
   stand-in / shop-approval eligibility check).
   - **Expect**: refused with a clear "verify your email" message.
4. `POST /api/auth/verify-email/request` to resend, then attempt the *old* token again.
   - **Expect**: old token now invalid (superseded), new token (from console output) works.
5. Use an already-consumed token again.
   - **Expect**: `400`, invalid/expired message (or "already verified" if it's that account's
     current state — spec AC6).

## Scenario 5 — Password reset (User Story 5 / P5)

1. `POST /api/auth/password-reset/request` with a registered email.
   - **Expect**: `202` with the generic confirmation message; console log shows the reset email
     with a token/link.
2. `POST /api/auth/password-reset/request` with an email that does not exist.
   - **Expect**: `202` with the **same** confirmation message (no enumeration — SC-010).
3. `POST /api/auth/password-reset/confirm` with the real token and a new password.
   - **Expect**: `200`; logging in with the old password now fails, logging in with the new
     password succeeds.
4. Confirm all previously issued access/refresh tokens for that account are now invalid (e.g. a
   refresh attempt using a pre-reset refresh cookie fails `401`) — validates FR-031.
5. Reuse the same reset token a second time.
   - **Expect**: `400`, invalid/expired.

## Done criteria for this feature

- All five scenarios above pass manually (or via the equivalent `pytest` suite in
  `backend/tests/accounts` and `backend/tests/vendors`) against a real Postgres database with
  migrations applied — not mocked.
- No plaintext password appears in the database or in server logs at any point during the above
  (Constitution Principle III / SC-007) — spot-check by inspecting the `auth_user`/custom user
  table and console output.

# API Contract: Accounts & Authentication

Base path: `/api/auth/` (registration/login/tokens/profile/verification/reset) and
`/api/vendor/` + `/api/admin/` (shop management). All bodies are JSON. All endpoints requiring
authentication expect `Authorization: Bearer <access_token>`. The refresh token is never present
in any request/response body — it travels only as an httpOnly cookie set/read by the server.

Traceability: each endpoint references the FR(s) it satisfies.

## Registration & Login

### `POST /api/auth/register/customer`
Satisfies FR-001, FR-004, FR-006, FR-021, FR-022.

Request:
```json
{ "name": "Ama Owusu", "email": "ama@example.com", "password": "•••••••••" }
```
Response `201`:
```json
{
  "access": "<jwt>",
  "user": { "id": "...", "name": "Ama Owusu", "email": "ama@example.com",
            "role": "CUSTOMER", "is_email_verified": false }
}
```
Sets refresh-token httpOnly cookie. Sends verification email (fire-and-forget; failure to send
does not fail registration). Errors: `400` duplicate email (FR-001 AC2), weak password (FR-021).

### `POST /api/auth/register/vendor`
Satisfies FR-002, FR-004, FR-005, FR-006, FR-021, FR-022.

Request:
```json
{ "name": "Kofi Mensah", "email": "kofi@example.com", "password": "•••••••••",
  "shop_name": "Kofi's Electronics" }
```
Response `201`: same shape as customer registration, `role: "VENDOR"`, plus
`"shops": [{ "id": "...", "name": "Kofi's Electronics", "status": "PENDING" }]`.
Errors: `400` duplicate email, duplicate shop name (User Story 2 AC5), weak password.

### `POST /api/auth/login`
Satisfies FR-007, FR-008.

Request: `{ "email": "...", "password": "..." }`
Response `200`: `{ "access": "<jwt>", "user": { ...same profile shape... } }`, sets refresh cookie.
Error `401`: `{ "detail": "Invalid email or password." }` — identical message regardless of which
field was wrong (FR-008).

### `POST /api/auth/logout`
Satisfies FR-009, FR-012. Auth required.

No body required. Blacklists the refresh token in the current request's cookie, clears the cookie.
Response `204`.

### `POST /api/auth/refresh`
Satisfies FR-010, FR-011. Reads the refresh token from the httpOnly cookie (no body needed).

Response `200`: `{ "access": "<new jwt>" }`. If rotation is enabled, also rotates and re-sets the
refresh cookie. Error `401` if the refresh token is missing/expired/blacklisted — frontend then
signs the user out locally.

### `GET /api/auth/me`
Satisfies FR-013. Auth required.

Response `200`:
```json
{
  "id": "...", "name": "...", "email": "...", "role": "VENDOR",
  "is_email_verified": true,
  "shops": [
    { "id": "...", "name": "Kofi's Electronics", "status": "APPROVED" },
    { "id": "...", "name": "Kofi's Repairs", "status": "PENDING" }
  ]
}
```
`shops` present only when `role == "VENDOR"`.

## Email Verification

### `POST /api/auth/verify-email/request`
Satisfies FR-025. Auth required (resend for the current unverified user).

No body. Issues a new `EmailVerificationToken`, invalidates prior unused ones (FR-026), sends
email. Response `202` regardless of current verification state (idempotent-feeling; if already
verified, response still `202` but no email is sent — avoids leaking internal state via status
code alone, though the body may say so for a good UX per spec AC6).

### `POST /api/auth/verify-email/confirm`
Satisfies FR-023, FR-026. No auth required (token itself is the credential).

Request: `{ "token": "..." }`
Response `200`: `{ "detail": "Email verified." }` or, if already verified via this same account,
`{ "detail": "Email already verified." }` (AC6 — not an error).
Error `400`: `{ "detail": "This verification link is invalid or has expired." }` (AC5).

## Password Reset

### `POST /api/auth/password-reset/request`
Satisfies FR-027, FR-028, FR-029. No auth required.

Request: `{ "email": "..." }`
Response `202` **always**, identical body regardless of whether the email is registered:
`{ "detail": "If that email is registered, a reset link has been sent." }` (FR-028, SC-010).

### `POST /api/auth/password-reset/confirm`
Satisfies FR-030, FR-031, FR-032. No auth required (token is the credential).

Request: `{ "token": "...", "new_password": "•••••••••" }`
Response `200`: `{ "detail": "Password updated. Please log in again." }`. Server-side, in one
transaction: validates password strength (FR-021), sets new hashed password, marks the token used,
blacklists every outstanding refresh token for that user (FR-031).
Error `400`: invalid/expired/already-used token, or weak password.

## Vendor Shop Management

### `GET /api/vendor/shops`
Satisfies FR-013 (shop list variant), supports User Story 2 AC3. Auth required, role=VENDOR.

Response `200`: list of the current Vendor's own shops (queryset filtered by `owner=request.user`
— Constitution "Security" non-functional requirement), each with `id`, `name`, `status`,
`status_reason`, `created_at`.

### `POST /api/vendor/shops`
Satisfies FR-002 (additional shops), FR-005, FR-019. Auth required, role=VENDOR.

Request: `{ "name": "New Shop Name" }`
Response `201`: the new shop, `status: "PENDING"`. Error `400` duplicate name (AC5).

## Administrator Shop Approval

### `GET /api/admin/shops?status=PENDING`
Satisfies FR-016. Auth required, role=ADMINISTRATOR.

Response `200`: paginated list of shops (Constitution "Resource Utilization" — list endpoints
paginated), each including owner name/email for context, filterable by `status` query param.

### `POST /api/admin/shops/{id}/approve`
Satisfies FR-017. Auth required, role=ADMINISTRATOR. Only valid from `status=PENDING` (`409`/`400`
otherwise). Response `200`: updated shop, `status: "APPROVED"`.

### `POST /api/admin/shops/{id}/reject`
Satisfies FR-018. Auth required, role=ADMINISTRATOR. Only valid from `status=PENDING`.

Request (optional): `{ "reason": "..." }`
Response `200`: updated shop, `status: "REJECTED"`, `status_reason` set if provided.

## Cross-cutting error shape

All error responses use a consistent envelope: `{ "detail": "..." }` for single-message errors, or
`{ "field_name": ["message", ...] }` for field-level validation errors (DRF default), so the
frontend has one predictable shape to render.

## Authorization summary (server-side enforcement, Constitution Principle I)

| Endpoint | Required role | Object-level check |
|---|---|---|
| `register/*`, `login`, `refresh`, `password-reset/*`, `verify-email/confirm` | none (anonymous) | — |
| `logout`, `me`, `verify-email/request` | any authenticated user | acts on `request.user` only |
| `GET/POST /api/vendor/shops` | VENDOR | list/create scoped to `owner=request.user` |
| `GET/POST /api/admin/shops/*` | ADMINISTRATOR | none beyond role (admin sees all shops) |

# Phase 1 Data Model: Accounts & Authentication

Source: `spec.md` Key Entities, Functional Requirements FR-001–FR-032. All fields below live in
PostgreSQL (Constitution Principle IV: the schema is "real core", not mocked).

## User (`apps/accounts/models.py`, `AUTH_USER_MODEL`)

Extends `AbstractBaseUser` + `PermissionsMixin`.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID/BigAutoField (PK) | |
| `email` | `EmailField`, unique | Normalized to lowercase on save — enforces spec FR-004 (case-insensitive uniqueness) without a DB extension |
| `name` | `CharField` | |
| `password` | inherited hashed field | Django's default PBKDF2 hasher; never plaintext (FR-006) |
| `role` | `CharField` with choices `CUSTOMER` / `VENDOR` / `ADMINISTRATOR` | Exactly one role per account (spec Key Entities); Administrator is never set via self-registration (FR-003) |
| `is_email_verified` | `BooleanField`, default `False` | Flips to `True` via email verification flow (FR-023) |
| `is_active` | `BooleanField`, default `True` | Standard Django flag; reserved for future account-disable use, not exercised by this feature |
| `date_joined` | `DateTimeField(auto_now_add=True)` | |

`USERNAME_FIELD = "email"`. No separate `username` field — email is the login identifier.

**Validation rules**:
- Email uniqueness enforced at the DB level (`unique=True` on the normalized column) — FR-004.
- Password strength (minimum length, at minimum) validated at the serializer layer using Django's
  built-in password validators before hashing — FR-021.
- `role` is set once at registration and not user-editable afterward through any endpoint in this
  feature.

**Relationships**: One `User` (role=`VENDOR`) → many `Shop` (see below). One `User` → many
`EmailVerificationToken` / `PasswordResetToken` (history of issued tokens; only the latest unused,
unexpired one per purpose is valid at a time per FR-026/FR-032).

## Shop (`apps/vendors/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID/BigAutoField (PK) | |
| `owner` | `ForeignKey(User)`, `on_delete=CASCADE`, related_name=`shops` | **Not** unique — a Vendor may own multiple shops (spec User Story 2 / FR-019) |
| `name` | `CharField`, unique | Unique across *all* shops, not just per-vendor (spec Assumptions) — FR-005 |
| `status` | `CharField` with choices `PENDING` / `APPROVED` / `REJECTED`, default `PENDING` | Set only by an Administrator action after creation (Constitution Principle II) — FR-014 |
| `status_reason` | `TextField`, nullable | Optional reason set on rejection, visible to the owning Vendor — FR-018 |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `status_changed_at` | `DateTimeField`, nullable, updated whenever `status` changes | Supports admin auditability and the "status-last-changed" attribute from spec Key Entities |

**Validation rules**:
- `owner.role` MUST be `VENDOR` (enforced at the serializer/view layer when a shop is created).
- Only PENDING shops can transition to APPROVED or REJECTED (state machine; an already-resolved
  shop is not re-approved/re-rejected — a new request is a new PENDING event per FR-019, which in
  practice is a *new* `Shop` row with a new name, since `name` is unique and a REJECTED shop keeps
  its REJECTED status as history rather than being reset to PENDING in place).
- Vendor-only actions (future catalog/order features) check `status == 'APPROVED'` **and**
  ownership for the *specific* shop being acted on — never account-wide (FR-015).

**State machine**:

```
        (Vendor creates shop request)
                    │
                    ▼
                PENDING ──(Admin approves)──► APPROVED
                    │
                    └────(Admin rejects)────► REJECTED
```

APPROVED and REJECTED are terminal for that specific `Shop` row; a Vendor recovers from REJECTED
by submitting a new shop-creation request (a new `Shop` row, new PENDING status) rather than by
mutating the rejected row, preserving history for the Administrator.

## EmailVerificationToken (`apps/accounts/models.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID/BigAutoField (PK) | |
| `user` | `ForeignKey(User)`, `on_delete=CASCADE`, related_name=`email_verification_tokens` | |
| `token` | `CharField`, unique, indexed | Opaque random value via `secrets.token_urlsafe(32)` |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `expires_at` | `DateTimeField` | `created_at` + 24h (research.md §3) |
| `used_at` | `DateTimeField`, nullable | Set when the token is successfully consumed; a token with `used_at` set is never valid again (FR-026) |

**Validation rules**: valid iff `used_at is None and expires_at > now()`. Issuing a new token for a
user invalidates (marks used) that user's other unused tokens of this type (FR-026's "resend"
behavior stays sane — only the newest link works).

## PasswordResetToken (`apps/accounts/models.py`)

Same shape as `EmailVerificationToken`, separate table (separate purpose/expiry):

| Field | Type | Notes |
|---|---|---|
| `id` | UUID/BigAutoField (PK) | |
| `user` | `ForeignKey(User)`, `on_delete=CASCADE`, related_name=`password_reset_tokens` | |
| `token` | `CharField`, unique, indexed | Opaque random value |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `expires_at` | `DateTimeField` | `created_at` + 1h (research.md §3 — shorter than verification, higher-risk action) |
| `used_at` | `DateTimeField`, nullable | |

**Validation rules**: same validity rule as above. Issuing a new reset token invalidates the
user's other unused reset tokens (FR-032). Successfully consuming a token to set a new password
MUST, in the same transaction, blacklist all of that user's currently-valid refresh tokens
(FR-031) — implemented via `simplejwt`'s token blacklist app keyed on `user`.

## Session (conceptual — no dedicated table)

Represented entirely by `simplejwt` access/refresh token pairs plus the refresh-token blacklist
table that `simplejwt`'s `token_blacklist` app already provides. No custom `Session` model is
needed; "logging out" = blacklisting that session's refresh token, "password reset invalidates all
sessions" = blacklisting every outstanding refresh token for that user.

## Cross-entity invariants (enforced in code, not just documented)

- A `User` with `role != VENDOR` MUST have zero associated `Shop` rows.
- `Shop.status` transitions only PENDING → APPROVED or PENDING → REJECTED, only via an
  Administrator-only endpoint, only inside a DB transaction (Constitution "Reliability").
- Every list endpoint returning `Shop` or `User` data filters by the requesting user's own
  ownership/role at the queryset level (Constitution "Security" non-functional requirement) —
  e.g. a Vendor's "my shops" endpoint filters `Shop.objects.filter(owner=request.user)`, never
  relying on a serializer-level field hide.

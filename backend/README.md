# emall backend

Django + Django REST Framework API for the emall project's Accounts & Authentication
(`specs/001-accounts-auth/`) and Product Catalog (`specs/002-product-catalog/`) features, plus
Shopping Cart & Checkout (`specs/003-cart-checkout/`) and Vendor Order Fulfillment
(`specs/004-order-fulfillment/`).

## Prerequisites

- Python 3.12
- PostgreSQL, reachable via `DATABASE_URL` (a `docker-compose.yml` is provided at the repo root and
  runs Postgres 16 on host port **5433**, to avoid clashing with a local Postgres install)
- Node 20.x, only needed if you're also running `frontend/`

## Setup

From the repo root:

```powershell
docker compose up -d
```

From `backend/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# then edit .env: set SECRET_KEY and ADMIN_SEED_PASSWORD to real values for your machine

python manage.py migrate
python manage.py seed_admin
python manage.py runserver
```

`GET http://localhost:8000/api/auth/me` should now return `401` (not a connection error).

## Environment variables

All required variables are documented with inline comments in `backend/.env.example`. Copy it to
`backend/.env` (gitignored, never commit real secrets) and fill in:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local dev |
| `ALLOWED_HOSTS` | comma-separated hostnames |
| `DATABASE_URL` | Postgres connection string, e.g. `postgres://emall:emall_dev_password@localhost:5433/emall` |
| `CORS_ALLOWED_ORIGINS` | frontend origin(s), e.g. `http://localhost:3000` |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` in dev — verification and password-reset emails print to the `runserver` console instead of sending real mail |
| `DEFAULT_FROM_EMAIL` | from-address used on those console emails |
| `ACCESS_TOKEN_LIFETIME_MINUTES` / `REFRESH_TOKEN_LIFETIME_DAYS` | simplejwt token lifetimes |
| `ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD` / `ADMIN_SEED_NAME` | used only by `seed_admin` (below) |

## Seeding the Administrator account

Administrator accounts are never created through a public registration endpoint. Run:

```powershell
python manage.py seed_admin
```

This creates (or updates, if it already exists) the Administrator user from `ADMIN_SEED_EMAIL` /
`ADMIN_SEED_PASSWORD` / `ADMIN_SEED_NAME` in `.env`.

## Product Catalog (`catalog` app)

- `requirements.txt` includes `Pillow` (research.md §1) — required for `ImageField` (product
  photos) and for validating uploaded files are genuine images, not just correctly-named files.
- Uploaded product images are written to `MEDIA_ROOT` and served from `MEDIA_URL` (both configured
  in `config/settings.py`; `MEDIA_ROOT` defaults to `backend/media/`, gitignored). In `DEBUG` mode
  Django serves `MEDIA_URL` directly — no separate static file server is needed for local dev.
- Each image upload is capped at 5MB (`MAX_PRODUCT_IMAGE_SIZE_BYTES` in
  `apps/catalog/serializers.py`) and validated as a real image, not just its declared content type.
- `python manage.py migrate` also applies `0002_seed_categories`, which seeds the fixed
  Administrator-owned category list (`apps/catalog/migrations/0002_seed_categories.py`) — no
  separate seed command is needed for categories.

## Shopping Cart & Checkout (`cart`, `orders`, `payments` apps)

- Three apps, no new dependencies — `requirements.txt` is unchanged from Product Catalog
  (research.md §7). Each app is thin and single-purpose: `cart` (persistent per-Customer cart),
  `orders` (checkout + order history, exposed at `/api/checkout/`, `/api/orders/`), `payments`
  (`PaymentRecord` only — no endpoints of its own).
- Payment is a swappable mock service (`apps/payments/services.py`, mirroring
  `apps/core/email.py`'s `EmailService` pattern): `charge()` takes only an opaque `method` label
  string (e.g. `"card"`), never raw card fields. `MockPaymentService` succeeds for any `method`
  except the case-insensitive sentinel `"declined"`, which deterministically fails — use it to
  exercise the payment-declined path in manual testing (research.md §5).
- Cart line prices/availability are always read live from the current `Product` (never frozen at
  add-to-cart time), so a vendor changing a product's price or publish status is reflected in every
  Customer's cart immediately.

## Vendor Order Fulfillment (`orders` app extension)

- No new Django app or dependency — this feature widens the existing `orders` app
  (`specs/004-order-fulfillment/`, research.md §6).
- `OrderItem.status` now supports the full lifecycle
  `PENDING → PROCESSING → SHIPPED → DELIVERED`, plus `CANCELLED` (reachable only from `PENDING` or
  `PROCESSING`, never from `SHIPPED`). Every transition is validated against a fixed adjacency map
  in `apps/orders/services.py`'s `advance_order_item_status()` — the only path that ever changes
  the status — which rejects any other requested pair (backward, skipped, or from a terminal
  state) without writing anything.
- Cancelling a line restores its quantity to the product's `stock_quantity` inside the same atomic
  transaction as the status change (`select_for_update` on the product row).
- Every status change is recorded in the new `OrderItemStatusEvent` history table
  (`order_item`, `status`, `changed_at`).
- New endpoints:
  - `GET /api/vendor/order-items/` / `PATCH /api/vendor/order-items/{id}/status/` — a Vendor's own
    order lines across every Customer's order, scoped by product-shop ownership at the queryset
    level (cross-vendor access 404s, not 403s). A Vendor's response never includes
    `status_history`.
  - `GET /api/admin/order-items/` — read-only Administrator oversight across every shop's order
    lines, the only response shape that includes a `status_history` array.

## Running the frontend alongside

```powershell
# from frontend/, in a separate terminal
copy .env.local.example .env.local
npm install
npm run dev
```

## Tests

```powershell
python -m manage.py migrate  # not required for tests — pytest-django manages its own test DB
pytest
```

Tests run against the real Postgres connection from `DATABASE_URL` (pytest-django creates and
migrates a separate `test_<db>` database automatically) — nothing is mocked at the database layer.

## Manual end-to-end validation

`specs/001-accounts-auth/quickstart.md` has five scripted scenarios (customer auth, vendor
shops, admin approval, email verification, password reset) to run against a live server and
real database.

`specs/002-product-catalog/quickstart.md` has five more (vendor create/publish/unpublish, the
shop-approval gate, public browse/search/filter, out-of-stock display, input validation).

`specs/003-cart-checkout/quickstart.md` has five more (persistent cart management, checkout and
order placement, cart reacting to live catalog changes, order history, and validation/edge cases
including the concurrent-oversell race).

`specs/004-order-fulfillment/quickstart.md` has five more (vendor fulfillment lifecycle, customer
visibility into fulfillment progress, invalid-transition rejection, stock restoration on
cancellation, and admin oversight with status history).

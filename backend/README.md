# emall backend

Django + Django REST Framework API for the emall project's Accounts & Authentication feature
(`specs/001-accounts-auth/`).

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

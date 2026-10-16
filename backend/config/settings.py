"""
Django settings for the E-Mall backend (feature 001-accounts-auth).

Config is entirely environment-driven per Constitution Principle III ("Secrets ... MUST come
from environment variables, never committed to the repository") and the "Portability" NFR
("configuration ... MUST be environment-driven so the same codebase runs in local dev and any
future deployment target without code changes").
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
# Needed for Django admin's CSRF check once it's served over HTTPS (e.g. https://api.mangimall.com).
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# In production Caddy terminates TLS and forwards plain HTTP; trust its X-Forwarded-Proto header
# so request.is_secure() is True (see docker-compose.prod.yml).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    # Project apps (Constitution "Maintainability": Django app boundaries)
    "apps.core",
    "apps.accounts",
    "apps.vendors",
    "apps.catalog",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.feedback",
    "apps.delivery",
    "apps.finance",
    "apps.realtime",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collectstatic output (Django admin CSS/JS) straight from gunicorn in production.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
# Served by gunicorn's uvicorn workers so `/ws/` (apps.realtime) runs beside the REST API.
ASGI_APPLICATION = "config.asgi.application"

# Realtime fan-out between worker processes. Without REDIS_URL (local dev, tests, CI) the
# in-memory layer only reaches sockets in the same process, which is enough for one worker.
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


# Database — PostgreSQL, the "real core" per Constitution Principle IV
DATABASES = {
    "default": env.db("DATABASE_URL"),
}


# Custom user model (feature 001-accounts-auth, task T011)
AUTH_USER_MODEL = "accounts.User"


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Product images (feature 002-product-catalog) — local disk for dev, behind Django's Storage
# API so swapping to a cloud backend later is a settings change, not a rewrite (Constitution
# Principle IV: Real Core, Mocked Edges).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Object storage (MinIO locally/in CI staging; swappable for real S3/R2 later without code
# changes, per the comment above). Off by default so the test suite stays hermetic — only
# opt in where a MinIO service actually exists (local docker-compose, staging simulation).
USE_S3_MEDIA = env.bool("USE_S3_MEDIA", default=False)
if USE_S3_MEDIA:
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    # In-network endpoint Django uses to talk to MinIO (e.g. http://minio:9000 inside
    # docker-compose). This is NOT necessarily the host a browser can reach — see
    # AWS_S3_CUSTOM_DOMAIN below.
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
    # Public host used when building URLs returned to clients (e.g. localhost:9000 locally).
    # Falls back to AWS_S3_ENDPOINT_URL (bucket included in the path) when unset. If set, it
    # MUST include the bucket name (e.g. "localhost:9000/emall-media") — django-storages
    # assumes a custom domain already maps to a bucket (virtual-hosted-style), which isn't
    # true for MinIO's path-style addressing, so the bucket has to be spelled out here.
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
    # MinIO runs without TLS in local dev / the CI staging simulation.
    AWS_S3_URL_PROTOCOL = env("AWS_S3_URL_PROTOCOL", default="http:")
    AWS_S3_ADDRESSING_STYLE = "path"  # required for MinIO's custom endpoint
    AWS_QUERYSTRING_AUTH = False  # public-read bucket: permanent, non-expiring URLs
    AWS_DEFAULT_ACL = "public-read"


# --- REST Framework -----------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "password_reset": "5/min",
        "verify_email": "5/min",
        "otp_confirm": "10/min",
        # Vendor registration checks an existing customer's password, so it is a login too.
        "register": "5/min",
        # Guest checkout: anonymous cart/checkout/order-tracking traffic, counted per IP.
        "guest_cart": "60/min",
        "guest_checkout": "10/min",
        "guest_order": "30/min",
    },
}

# Throttle counters live here. A database cache is shared by every gunicorn worker and survives
# restarts; the per-process default would multiply each limit by the worker count. The table is
# created by `manage.py createcachetable` (docker-compose command; the test runner does it itself).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# --- Payouts to shop owners ----------------------------------------------
# Which `apps.finance.disbursement` adapter sends vendor payouts ("mock" until a real
# mobile-money provider is integrated).
DISBURSEMENT_BACKEND = env("DISBURSEMENT_BACKEND", default="mock")

# --- Customer payments (AzamPay mobile money) -------------------------------
# Which `apps.payments` mobile-money gateway takes customer payments at checkout:
#   "mock"              - synchronous MockPaymentService only (tests, default)
#   "azampay_simulator" - local stand-in for the AzamPay sandbox: pushes are approved/rejected
#                         from the dev phone page (/dev/azampay-sandbox), no credentials needed
#   "azampay"           - the real AzamPay API (sandbox or live, chosen by the URLs below)
PAYMENT_BACKEND = env("PAYMENT_BACKEND", default="mock")
AZAMPAY_APP_NAME = env("AZAMPAY_APP_NAME", default="")
AZAMPAY_CLIENT_ID = env("AZAMPAY_CLIENT_ID", default="")
AZAMPAY_CLIENT_SECRET = env("AZAMPAY_CLIENT_SECRET", default="")
AZAMPAY_API_KEY = env("AZAMPAY_API_KEY", default="")
AZAMPAY_AUTH_URL = env("AZAMPAY_AUTH_URL", default="https://authenticator-sandbox.azampay.co.tz")
AZAMPAY_API_URL = env("AZAMPAY_API_URL", default="https://sandbox.azampay.co.tz")
# AzamPay doesn't sign callbacks, so the callback URL carries this secret instead:
# {BACKEND_PUBLIC_URL}/api/payments/azampay/callback/<AZAMPAY_CALLBACK_TOKEN>
AZAMPAY_CALLBACK_TOKEN = env("AZAMPAY_CALLBACK_TOKEN", default="dev-callback-token")
BACKEND_PUBLIC_URL = env("BACKEND_PUBLIC_URL", default="http://localhost:8000")
# A push the customer never answers is failed (and its stock released) after this long.
PAYMENT_PENDING_TIMEOUT_MINUTES = env.int("PAYMENT_PENDING_TIMEOUT_MINUTES", default=15)
# The mock card approves every charge: dev/tests only, never production.
MOCK_CARD_PAYMENTS_ENABLED = env.bool("MOCK_CARD_PAYMENTS_ENABLED", default=DEBUG)

# --- Manual payments (no gateway; an administrator confirms the money arrived) --------------
# Any of "cod" (cash on delivery) and "lipa_namba" (customer pays the till below, then enters
# the transaction ID), comma-separated; empty turns both off.
MANUAL_PAYMENT_METHODS = env.list("MANUAL_PAYMENT_METHODS", default=["cod", "lipa_namba"])
LIPA_NAMBA_TILL = env("LIPA_NAMBA_TILL", default="")
LIPA_NAMBA_NAME = env("LIPA_NAMBA_NAME", default="MangiMall")
# An unconfirmed Lipa Namba order is failed (and its stock released) after this long.
MANUAL_PAYMENT_TIMEOUT_HOURS = env.int("MANUAL_PAYMENT_TIMEOUT_HOURS", default=24)

# --- simplejwt (task T013) -----------------------------------------------
# Access token stays short-lived and is returned to the frontend in the response body only
# (held in memory there); refresh token is longer-lived and is set exclusively as an
# httpOnly/Secure/SameSite cookie by our own views (see apps/accounts/views.py), never
# returned in a JSON body — Constitution Principle III.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Name of the httpOnly cookie carrying the refresh token (never read by frontend JS).
# Namespaced (not a generic "refresh_token") because cookies are shared across all ports on
# "localhost" in local dev — a generic name collides with other same-machine projects' cookies of
# the same name, and Django's cookie parsing silently keeps only the last one it sees.
REFRESH_TOKEN_COOKIE_NAME = env("REFRESH_TOKEN_COOKIE_NAME", default="emall_refresh_token")
REFRESH_TOKEN_COOKIE_PATH = "/api/auth/"
# Secure=False only makes sense over plain-HTTP local dev; flip to True behind HTTPS.
REFRESH_TOKEN_COOKIE_SECURE = not DEBUG
REFRESH_TOKEN_COOKIE_SAMESITE = "Lax"

# httpOnly cookie identifying an anonymous guest's server-side cart (guest checkout). Path covers
# both /api/cart and /api/checkout, plus /api/auth/login where a guest cart is merged on sign-in.
GUEST_CART_COOKIE_NAME = env("GUEST_CART_COOKIE_NAME", default="emall_guest_cart")
GUEST_CART_COOKIE_PATH = "/api/"
GUEST_CART_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


# --- CORS (task T017) -----------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True


# --- Email (task T015 — the deliberately mocked edge, Constitution Principle IV) ----------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@emall.local")
# SMTP transport (e.g. Gmail: smtp.gmail.com:587 + TLS + an App Password). Only read when
# EMAIL_BACKEND is django.core.mail.backends.smtp.EmailBackend.
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:3000")

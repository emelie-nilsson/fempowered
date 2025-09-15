import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import mimetypes

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env locally (Heroku uses Config Vars)
load_dotenv(dotenv_path=BASE_DIR / ".env")


# Ensure correct content types for assets that Python's mimetypes may not know on Windows
mimetypes.add_type("image/webp", ".webp", True)
mimetypes.add_type("image/svg+xml", ".svg", True)


# Core security & env


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-change-me")

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")

# Allow extra hosts via env in prod, and default to .herokuapp.com
if not DEBUG:
    ALLOWED_HOSTS += env_list("ALLOWED_HOSTS_EXTRA", "")
    if all("herokuapp.com" not in h for h in ALLOWED_HOSTS):
        ALLOWED_HOSTS.append(".herokuapp.com")

# CSRF
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://127.0.0.1:8000,"
    "http://localhost:8000,"
    "https://127.0.0.1:8000,"
    "https://localhost:8000,"
    "https://*.herokuapp.com",
)

# Optional explicit Heroku app domain (e.g. fempowered-12345.herokuapp.com)
HEROKU_APP_DOMAIN = os.getenv("HEROKU_APP_DOMAIN", "").strip()
if HEROKU_APP_DOMAIN:
    origin = f"https://{HEROKU_APP_DOMAIN}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)


# Stripe

STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_CURRENCY = os.getenv("STRIPE_CURRENCY", "eur")

# Feature flags
TEST_ALLOW_REVIEW_WITHOUT_PURCHASE = DEBUG  # allow in dev, off in prod


# Django apps

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # 3rd party apps
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "whitenoise.runserver_nostatic",
    # Apps
    "home",
    "shop",
    "accounts",
    "checkout",
    "contact",
    # Dev-tools (optional)
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fempowered.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # allauth needs this
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "shop.context_processors.cart_counter",
            ],
            "builtins": [
                "django.templatetags.i18n",
                "django.templatetags.static",
                "home.templatetags.form_tags",
                "shop.templatetags.image_urls",
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = True
ACCOUNT_USERNAME_MIN_LENGTH = 4
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"

WSGI_APPLICATION = "fempowered.wsgi.application"


# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Heroku Postgres via DATABASE_URL (Heroku Config Vars)
if os.environ.get("DATABASE_URL"):
    DATABASES["default"] = dj_database_url.config(conn_max_age=600, ssl_require=True)


#  Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization / Timezone

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Stockholm"
USE_I18N = True
USE_TZ = True


# Static & Media
# WhiteNoise for static, local filesystem for media (both dev & prod)

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "media",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    # Static files via WhiteNoise
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    # Media files stored on local filesystem
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Avoid 500 if manifest file missing after first collectstatic
WHITENOISE_MANIFEST_STRICT = False


# Email

CONTACT_RECIPIENTS = env_list("CONTACT_RECIPIENTS", "info@fempowered.com")

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "Fempowered <no-reply@example.local>"
    ACCOUNT_EMAIL_VERIFICATION = "optional"
else:
    EMAIL_BACKEND = os.getenv(
        "EMAIL_BACKEND",
        "django.core.mail.backends.smtp.EmailBackend",
    ).strip()
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "apikey")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Fempowered <no-reply@fempowered.shop>")
    SERVER_EMAIL = os.getenv("SERVER_EMAIL", "no-reply@fempowered.shop")
    ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "mandatory")


# Security dev vs prod

# Harden common defaults
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
USE_X_FORWARDED_HOST = True

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"
else:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Heroku router
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"


# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "ERROR", "propagate": True},
        "django.server": {"handlers": ["console"], "level": "ERROR", "propagate": True},
    },
}

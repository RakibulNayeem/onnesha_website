"""
Django settings for the Onnesha coaching-centre finance system.

Everything that changes between your laptop and the cloud is read from
environment variables, so you never edit this file after deployment.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-only-key-change-me-before-deploying-onnesha"
)
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h]
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "website",
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

ROOT_URLCONF = "onnesha_finance.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.centre_info",
                "core.context_processors.nav",
                "website.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "onnesha_finance.wsgi.application"

# --- Database -------------------------------------------------------------
# Local: SQLite file. Cloud: set DATABASE_URL to a Postgres connection string.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Dhaka")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Plain (unhashed) names - see WHITENOISE_USE_FINDERS below.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

# Vercel has no place to put a collectstatic build the app can read back,
# so WhiteNoise serves the files where they already live - this repo's
# static/ plus each app's own. Deploys that do run collectstatic (Render)
# are unaffected: STATIC_ROOT still wins when it is populated.
WHITENOISE_USE_FINDERS = True
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 7

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# --- Onnesha specific -----------------------------------------------------
CENTRE_NAME = os.environ.get("CENTRE_NAME", "\u0985\u09a8\u09cd\u09ac\u09c7\u09b7\u09be | Onnesha")
CENTRE_TAGLINE = os.environ.get(
    "CENTRE_TAGLINE", "\u098f\u0995\u09be\u09a1\u09c7\u09ae\u09bf\u0995 \u098f\u09a8\u09cd\u09a1 \u098f\u09a1\u09ae\u09bf\u09b6\u09a8 \u0995\u09c7\u09df\u09be\u09b0"
)
CENTRE_ADDRESS = os.environ.get(
    "CENTRE_ADDRESS", "Chowdhurypara, Town Colony Charmatha, Sherpur, Bogura"
)
CENTRE_PHONE = os.environ.get("CENTRE_PHONE", "")
STUDENT_ID_PREFIX = os.environ.get("STUDENT_ID_PREFIX", "ONS")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

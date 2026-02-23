import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------- SECURITY ----------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-please-change")
DEBUG = os.getenv("DEBUG", "True") == "True"
OTP_BYPASS = os.getenv("OTP_BYPASS", "True") == "True"

ALLOWED_HOSTS = [
    "*",
    os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
]

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ---------------- APPLICATIONS ----------------
INSTALLED_APPS = [
    "jazzmin",

    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Auth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Custom Apps
    "reports.apps.ReportsConfig",
    "widget_tweaks",
    "solo",
    "mathfilters",
    "accounts.apps.AccountsConfig",
    "khataapp",
    "core_settings",
    "rest_framework",
    "mobileapi",
    "chatbot",
    'commerce',
    'billing',        # <-- Add this
    'commerce',
]

# ---------------- NO ADDONS ----------------
# ❌ Removed All Addons — Not Needed & Missing in Project

SITE_ID = 1

# ---------------- CUSTOM USER MODEL ----------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ---------------- GOOGLE LOGIN ----------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["email", "profile", "openid"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ---------------- MIDDLEWARE ----------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "khataapp.middleware.RestrictAdminMiddleware",
    "core_settings.middleware.FeatureGateMiddleware",
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # ❌ Removed Addons Middleware
]

ROOT_URLCONF = "khatapro.urls"

# ---------------- TEMPLATES ----------------
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
                "core_settings.context_processors.global_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "khatapro.wsgi.application"

# ---------------- DATABASE ----------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

# ---------------- PASSWORD VALIDATION ----------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------- I18N / TIMEZONE ----------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------- STATIC & MEDIA ----------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------- LOGIN FLOW ----------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

ACCOUNT_ADAPTER = "accounts.adapters.OTPAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.OTPSocialAdapter"

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False

# ---------------- REST FRAMEWORK ----------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
    ),
}

# ---------------- OPENAI ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------- LOGGING ----------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ---------------- JAZZMIN ----------------
JAZZMIN_SETTINGS = {
    "site_title": "KhataBook Admin",
    "site_header": "KhataBook",
    "site_brand": "KhataBook",
    "site_logo": "img/logo.png",
    "login_logo": "img/logo.png",
    "welcome_sign": "Welcome to KhataBook Admin",
    "copyright": "KhataBook",
    "search_model": "accounts.User",
    "show_sidebar": True,
    "navigation_expanded": True,
    "order_with_respect_to": ["accounts", "khataapp", "core_settings", "mobileapi", "chatbot"],
}

JAZZMIN_UI_TWEAKS = {
    "theme": "default",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-primary",
}

# ---------------- CELERY (OPTIONAL) ----------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "")
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------- BASE DIR ----------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------- SECURITY ----------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "default-secret-key")
DEBUG = True

# TEMP: OTP bypass for Render free deploy
OTP_BYPASS = True

ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost"]
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ---------------- INSTALLED APPS ----------------
INSTALLED_APPS = [
    "jazzmin",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    "reports.apps.ReportsConfig",

    "widget_tweaks",
    "solo",
    "mathfilters",

    "accounts.apps.AccountsConfig",
    "khataapp",
    "billing",
    "commerce",
    "core_settings",
    "rest_framework",
    "mobileapi",
    "chatbot",
]

SITE_ID = 1

# ---------------- AUTH ----------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# ---------------- GOOGLE LOGIN ----------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_SECRET"),
            "key": "",
        },
        "SCOPE": ["email", "profile", "openid"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ---------------- MIDDLEWARE ----------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "khataapp.middleware.RestrictAdminMiddleware",
    "core_settings.middleware.FeatureGateMiddleware",

    "allauth.account.middleware.AccountMiddleware",
]

# ---------------- URL ----------------
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

# ---------------- WSGI ----------------
WSGI_APPLICATION = "khatapro.wsgi.application"

# ---------------- DATABASE ----------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

# ---------------- PASSWORD ----------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------- I18N ----------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------- STATIC ----------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------- LOGIN ----------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

ACCOUNT_ADAPTER = "accounts.adapters.OTPAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.OTPSocialAdapter"

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False

# ---------------- REST ----------------
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
    "order_with_respect_to": ["accounts", "khataapp", "billing", "commerce", "chatbot"],
    "icons": {
        "accounts.user": "fas fa-user",
        "khataapp.*": "fas fa-book",
        "billing.*": "fas fa-credit-card",
        "commerce.*": "fas fa-shopping-cart",
    },
}

JAZZMIN_UI_TWEAKS = {
    "theme": "default",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-primary",
}

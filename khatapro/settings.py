import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------- BASE DIR ----------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------- SECURITY ----------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "default-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*", "khataapp.pythonanywhere.com", "127.0.0.1", "localhost"]

# ---------------- INSTALLED APPS ----------------
INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.sites',
    # django-allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Third-party apps
    'widget_tweaks',

    # Your apps
    "accounts.apps.AccountsConfig",
    "khataapp",
    "billing",
    "commerce",
    'mathfilters',
    'core_settings',
    'rest_framework',
    'mobileapi',
    'chatbot',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": "941752724711-s6j8a0l7vj0dujnd1lnue7tf6ll7r8st.apps.googleusercontent.com",
            "secret": "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",
            "key": ""
        },
        "SCOPE": [
            "email",
            "profile",
            "openid",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

AUTH_USER_MODEL = "accounts.User"

# ---------------- MIDDLEWARE ----------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'khataapp.middleware.RestrictAdminMiddleware',
    # REQUIRED FOR ALLAUTH
    "allauth.account.middleware.AccountMiddleware",

]

# ---------------- ROOT URL ----------------
ROOT_URLCONF = "khatapro.urls"

# ---------------- TEMPLATES ----------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                "core_settings.context_processors.global_settings",
            ],
        },
    },
]

# ---------------- WSGI ----------------
WSGI_APPLICATION = "khatapro.wsgi.application"

# ---------------- Mobile APP Auth ----------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
}

# ---------------- DATABASE ----------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",   # You can switch to MySQL/Postgres if needed
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ---------------- PASSWORD VALIDATION ----------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------- LANGUAGE + TIME ----------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# ---------------- STATIC + MEDIA ----------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------- DEFAULT PK ----------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------- AUTH SETTINGS ----------------
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/verify-otp/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

ACCOUNT_ADAPTER = "accounts.adapters.OTPAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.OTPSocialAdapter"

ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_EMAIL_VERIFICATION = "none"


OPENAI_API_KEY = "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"


# ---------------- Logs ----------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },

    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_debug.log'),
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_error.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['file', 'console', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


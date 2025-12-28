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


    # Third-party apps
    "social_django",   # for Google login etc.
    'widget_tweaks',

    # Your apps
    "accounts.apps.AccountsConfig",
    "khataapp",
    "billing",
    "commerce",
    'mathfilters',
    'core_settings',
]

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
LOGIN_REDIRECT_URL = "/accounts/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ---------------- GOOGLE OAUTH ----------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

AUTH_USER_MODEL = "accounts.User"


# ---------------- SOCIAL AUTH ----------------
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = GOOGLE_CLIENT_ID
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = GOOGLE_CLIENT_SECRET

# ---------------- EMAIL (optional: for password reset, etc.) ----------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"



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


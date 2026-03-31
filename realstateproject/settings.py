import os
import socket
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------- DESKTOP RUNTIME ----------------
IS_FROZEN = bool(getattr(sys, "frozen", False))
# Treat PyInstaller builds as desktop mode even if a runtime hook imports settings
# before `run_desktop.py` can set environment variables.
DESKTOP_MODE = IS_FROZEN or (os.getenv("DESKTOP_MODE", "False").strip().lower() in {"1", "true", "yes", "on"})
RUNNING_RUNSERVER = "runserver" in sys.argv
RUNNING_TESTS = "test" in sys.argv

# Prefer a writable, persistent directory for desktop data (SQLite + uploads).
APP_DATA_DIR = Path(os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(BASE_DIR)) / "JaisTechKhataBook"
DESKTOP_DATA_DIR = APP_DATA_DIR if (IS_FROZEN or DESKTOP_MODE) else BASE_DIR

try:
    DESKTOP_DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    # If we can't create it (locked down machine), fallback to BASE_DIR.
    DESKTOP_DATA_DIR = BASE_DIR

# Load env in a PyInstaller-friendly way:
# 1) bundled .env (sys._MEIPASS) as defaults
# 2) project .env (BASE_DIR) as defaults
# 3) user-editable .env next to persistent desktop data dir as override
_meipass = getattr(sys, "_MEIPASS", None)
if _meipass:
    load_dotenv(dotenv_path=str(Path(_meipass) / ".env"), override=False)
load_dotenv(dotenv_path=str(BASE_DIR / ".env"), override=False)
load_dotenv(dotenv_path=str(DESKTOP_DATA_DIR / ".env"), override=True)

# ---------------- SECURITY ----------------
DEBUG = os.getenv("DEBUG", "False").strip().lower() in {"1", "true", "yes", "on"}
SECRET_KEY = (os.getenv("DJANGO_SECRET_KEY") or "").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-secret-key-please-change"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set when DEBUG=False")
OTP_BYPASS = os.getenv("OTP_BYPASS", "True") == "True"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "*").split(",") if h.strip()]
if os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.getenv("RENDER_EXTERNAL_HOSTNAME"))

# Desktop runs on localhost; ensure loopback hosts are always allowed even if the
# environment is configured for a cloud domain.
if DESKTOP_MODE and "*" not in ALLOWED_HOSTS:
    for _h in ("localhost", "127.0.0.1", "127.0.0.2"):
        if _h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_h)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
MAX_TEST_USERS = int(os.getenv("MAX_TEST_USERS", "10"))
DESKTOP_APP_VERSION = (os.getenv("DESKTOP_APP_VERSION_CODE") or os.getenv("DESKTOP_APP_VERSION") or "0.0.0").strip()
CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "False").strip().lower() in {"1", "true", "yes", "on"}
CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if x.strip()]

# ---------------- WhatsApp Web Gateway (QR) defaults ----------------
# Used by the user-side WhatsApp Setup Wizard to prefill gateway details.
WA_GATEWAY_BASE_URL = (os.getenv("WA_GATEWAY_BASE_URL") or "").strip()
WA_GATEWAY_API_KEY = (os.getenv("WA_GATEWAY_API_KEY") or "").strip()
WHATSAPP_GATEWAY_BASE_URL = (os.getenv("WHATSAPP_GATEWAY_BASE_URL") or WA_GATEWAY_BASE_URL or "").strip()
WHATSAPP_GATEWAY_API_KEY = (os.getenv("WHATSAPP_GATEWAY_API_KEY") or WA_GATEWAY_API_KEY or "").strip()

# Default country code for WhatsApp numbers (used to normalize 10-digit numbers like: 9555xxxxxx -> 91 + number)
WA_DEFAULT_COUNTRY_CODE = (os.getenv("WA_DEFAULT_COUNTRY_CODE") or os.getenv("WHATSAPP_DEFAULT_COUNTRY_CODE") or "").strip()

# India-first safe default (override via WA_DEFAULT_COUNTRY_CODE).
# This project defaults to `TIME_ZONE=Asia/Kolkata`, so assume +91 when unset.
_tz_guess = (os.getenv("TIME_ZONE") or "Asia/Kolkata").strip()
if not WA_DEFAULT_COUNTRY_CODE and _tz_guess in {"Asia/Kolkata", "Asia/Calcutta"}:
    WA_DEFAULT_COUNTRY_CODE = "91"

# Dev/demo defaults (safe to change in .env)
if DEBUG and not WA_GATEWAY_BASE_URL:
    WA_GATEWAY_BASE_URL = "http://127.0.0.1:3100"
if DEBUG and not WA_GATEWAY_API_KEY:
    WA_GATEWAY_API_KEY = "DEMO_WA_GATEWAY_KEY_CHANGE_ME"
if DEBUG and not WHATSAPP_GATEWAY_BASE_URL:
    WHATSAPP_GATEWAY_BASE_URL = WA_GATEWAY_BASE_URL
if DEBUG and not WHATSAPP_GATEWAY_API_KEY:
    WHATSAPP_GATEWAY_API_KEY = WA_GATEWAY_API_KEY

# Auto-start the bundled Node gateway during `manage.py runserver` (dev/desktop).
_wa_autostart_env = (os.getenv("WA_GATEWAY_AUTOSTART") or "").strip().lower()
if _wa_autostart_env in {"0", "false", "no", "off"}:
    WA_GATEWAY_AUTOSTART = False
elif _wa_autostart_env in {"1", "true", "yes", "on"}:
    WA_GATEWAY_AUTOSTART = True
else:
    # Default: keep gateway autostart OFF to avoid Windows pop-ups when the local
    # Node service is not installed. Enable explicitly via WA_GATEWAY_AUTOSTART=1.
    WA_GATEWAY_AUTOSTART = False

_SERVE_STATICFILES_ENV = os.getenv("SERVE_STATICFILES", "").strip().lower() in {"1", "true", "yes", "on"}
_base_url_l = (BASE_URL or "").strip().lower()
IS_LOCAL_BASE_URL = _base_url_l.startswith(("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"))
# Serve static/media via Django only for local/dev + Desktop builds.
SERVE_STATICFILES = bool(DEBUG or DESKTOP_MODE or RUNNING_RUNSERVER or IS_LOCAL_BASE_URL or _SERVE_STATICFILES_ENV)
CELERY_BROKER_URL_ENV = (os.getenv("CELERY_BROKER_URL") or "").strip()
CELERY_RESULT_BACKEND_ENV = (os.getenv("CELERY_RESULT_BACKEND") or "").strip()
REDIS_URL = os.getenv("REDIS_URL", "").strip()
CHANNEL_REDIS_URL = os.getenv("CHANNEL_REDIS_URL", REDIS_URL).strip()
_DISABLE_CELERY_ENV = os.getenv("DISABLE_CELERY", "False").strip().lower() in {"1", "true", "yes", "on"}
_CELERY_INFRA_CONFIGURED = bool(CELERY_BROKER_URL_ENV or CELERY_RESULT_BACKEND_ENV or REDIS_URL)


def _endpoint_available(url: str) -> bool:
    """
    Lightweight socket probe so local/dev runs can gracefully fallback when Redis
    is configured in .env but the service is not actually running.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"redis", "rediss"}:
            return True
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 6379
        timeout = float((os.getenv("REDIS_HEALTHCHECK_TIMEOUT") or "0.20").strip())
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
    except Exception:
        return True


_CELERY_BACKEND_REACHABLE = _endpoint_available(CELERY_BROKER_URL_ENV or REDIS_URL or CELERY_RESULT_BACKEND_ENV)
_CHANNEL_REDIS_REACHABLE = _endpoint_available(CHANNEL_REDIS_URL)
# Local/dev safety: don't keep trying Redis when it isn't actually reachable.
AUTO_DISABLE_CELERY = (DEBUG or RUNNING_RUNSERVER or IS_LOCAL_BASE_URL) and (
    (not _CELERY_INFRA_CONFIGURED) or (not _CELERY_BACKEND_REACHABLE)
)
DISABLE_CELERY = DESKTOP_MODE or _DISABLE_CELERY_ENV or AUTO_DISABLE_CELERY

# Shared token for offline-first clients (Desktop + Flutter) to push data when online.
# Set this in `.env` on the cloud/server deployment.
SYNC_API_TOKEN = (os.getenv("SYNC_API_TOKEN") or "").strip()
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
AGENT_PAYOUT_RATE = os.getenv("AGENT_PAYOUT_RATE", "0.10")

# ---------------- APPLICATIONS ----------------
INSTALLED_APPS = [
    "jazzmin",

    # Django Core
    # Daphne provides ASGI `runserver`. In desktop mode we prefer the built-in
    # Django runserver (WSGI) for maximum PyInstaller reliability.
    *([] if DESKTOP_MODE else ["daphne"]),
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

    # Platform Stack
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    # Channels is used for WebSocket features on the cloud/server deployment.
    # Desktop runs without Daphne/ASGI, so channels is optional there.
    *([] if DESKTOP_MODE else ["channels"]),

    # Custom Apps
    # "reports.apps.ReportsConfig",  # disabled for real-estate build
    "widget_tweaks",
    "solo",
    "mathfilters",
    "accounts.apps.AccountsConfig",
    "khataapp.apps.KhataappConfig",
    "core_settings",
    "sms_center.apps.SMSCenterConfig",
    "mobileapi",
    "chatbot",
    # "commerce.apps.CommerceConfig",  # disabled; module not required for real-estate build
    # "ledger.apps.LedgerConfig",  # disabled legacy ledger
    "billing.apps.BillingConfig",
    # "system_mode",
    "whatsapp.apps.WhatsAppConfig",
    # "ai_ocr.apps.AIOCRConfig",
    "voice.apps.VoiceConfig",
    # "ai_insights.apps.AIInsightsConfig",
    "validation.apps.ValidationConfig",
    # "bank_import.apps.BankImportConfig",
    # "procurement.apps.ProcurementConfig",
    # "smart_khata.apps.SmartKhataConfig",  # removed: module not present in real-estate build
    # "smart_bi.apps.SmartBIConfig",       # removed: module not present in real-estate build
    "event_bus.apps.EventBusConfig",

    # Universal SaaS Modules
    "users",
    "customers.apps.CustomersConfig",
    # legacy retail modules removed for real-estate build
    # "pos",
    # "printer_config",
    # "scanner_config",
    # "warehouse",
    # "products",
    # "orders",
    # legacy commerce apps removed
    # "commission",
    "payments.apps.PaymentsConfig",
    # "analytics",
    # "ai_engine",
    "realtime",
    # AgentFlow
    "agents.apps.AgentsConfig",
    "payouts.apps.PayoutsConfig",
    "rewards.apps.RewardsConfig",
    "visits.apps.VisitsConfig",
    "saas_core",
    "deals.apps.DealsConfig",
    "addons.group_plan_permissions",
    "addons.testing_access",
    "addons.plan_feature_sync",
    "whatsapp_gateway",
    "location.apps.LocationConfig",
    "hierarchy.apps.HierarchyConfig",
    "leads.apps.LeadsConfig",
    "marketing.apps.MarketingConfig",
    "notifications.apps.NotificationsConfig",
    "fraud_detection.apps.FraudDetectionConfig",
    "api_integrations.apps.APIIntegrationsConfig",
    "wallet.apps.WalletConfig",
    "kyc.apps.KycConfig",
    "crm.apps.CrmConfig",
    "communication.apps.CommunicationConfig",
    "intelligence.apps.IntelligenceConfig",
    "loans.apps.LoansConfig",
    "verification.apps.VerificationConfig",
    "schemes.apps.SchemesConfig",
    "content.apps.ContentConfig",
    "reviews.apps.ReviewsConfig",
    "subscription.apps.SubscriptionConfig",
    "performance.apps.PerformanceConfig",
]

# ---------------- ADDONS ----------------
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
    # WhiteNoise is useful in cloud/prod deployments for static files.
    # In desktop/local runserver mode, we serve static directly and avoid
    # relying on optional packaged dependencies.
    *([] if (DESKTOP_MODE or RUNNING_RUNSERVER) else ["whitenoise.middleware.WhiteNoiseMiddleware"]),

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "realstateproject.dev_cors.DevCorsMiddleware",
    *(["realstateproject.desktop_cache.NoCacheStaticMiddleware"] if DESKTOP_MODE else []),
    "core_settings.rate_limit.RateLimitMiddleware",
    *(["accounts.desktop_csrf.DesktopCsrfBypassMiddleware"] if (DESKTOP_MODE or RUNNING_RUNSERVER) else []),
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core_settings.jwt_middleware.JWTAuthenticationMiddleware",
    "leads.middleware.LeadLockMiddleware",
    "saas_core.middleware.CompanyResolverMiddleware",
    # "system_mode.middleware.SystemModeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core_settings.security_headers.SecurityHeadersMiddleware",

    # "khataapp.middleware.RestrictAdminMiddleware",
    "core_settings.middleware.FeatureGateMiddleware",
    'allauth.account.middleware.AccountMiddleware',

    # ❌ Removed Addons Middleware
]

ROOT_URLCONF = "realstateproject.urls"
TEST_RUNNER = "realstateproject.test_runner.AppOnlyDiscoverRunner"

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
                "accounts.context_processors.erp_role_context",
                "core_settings.context_processors.global_settings",
                # "system_mode.context_processors.system_mode_context",
            ],
        },
    },
]

WSGI_APPLICATION = "realstateproject.wsgi.application"
ASGI_APPLICATION = "realstateproject.asgi.application"

# ---------------- DATABASE ----------------
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=os.getenv("DB_SSL_REQUIRE", "False") == "True",
        )
    }
else:
    DB_ENGINE = (os.getenv("DB_ENGINE") or "").strip().lower()
    MYSQL_NAME = (os.getenv("MYSQL_NAME") or "").strip()

    if DB_ENGINE == "mysql" or MYSQL_NAME:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.mysql",
                "NAME": MYSQL_NAME or "real_estate_super_app",
                "USER": (os.getenv("MYSQL_USER") or "root").strip(),
                "PASSWORD": (os.getenv("MYSQL_PASSWORD") or "").strip(),
                "HOST": (os.getenv("MYSQL_HOST") or "127.0.0.1").strip(),
                "PORT": (os.getenv("MYSQL_PORT") or "3306").strip(),
                "OPTIONS": {
                    "charset": "utf8mb4",
                    "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                },
                "CONN_MAX_AGE": int((os.getenv("MYSQL_CONN_MAX_AGE") or "600").strip()),
            }
        }
    else:
        SQLITE_PATH = (os.getenv("SQLITE_PATH") or "").strip()
        if not SQLITE_PATH:
            SQLITE_PATH = str((DESKTOP_DATA_DIR / "db.sqlite3").resolve())

        # Desktop stability: reduce frequent open/close churn on Windows by keeping sqlite connections warm.
        try:
            _sqlite_conn_max_age = int(
                (os.getenv("SQLITE_CONN_MAX_AGE") or ("3600" if (DESKTOP_MODE or RUNNING_RUNSERVER) else "0")).strip()
            )
        except Exception:
            _sqlite_conn_max_age = 0

        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": SQLITE_PATH,
                "OPTIONS": {"timeout": int(os.getenv("SQLITE_TIMEOUT", "60"))},
                "CONN_MAX_AGE": _sqlite_conn_max_age,
            }
        }

# Channels: use Redis only when configured and reachable; otherwise fallback to in-memory.
if CHANNEL_REDIS_URL and _CHANNEL_REDIS_REACHABLE:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [CHANNEL_REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
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

# In PyInstaller builds, `sys._MEIPASS` points to the bundled resources folder
# (onedir: `<app>\_internal`, onefile: temp extract dir).
_MEIPASS_DIR = None
try:
    _MEIPASS_DIR = Path(getattr(sys, "_MEIPASS", "")).resolve() if IS_FROZEN else None
except Exception:
    _MEIPASS_DIR = None

_BUNDLED_STATIC_DIR = None
try:
    if _MEIPASS_DIR:
        candidate = (_MEIPASS_DIR / "static").resolve()
        if candidate.exists():
            _BUNDLED_STATIC_DIR = candidate
except Exception:
    _BUNDLED_STATIC_DIR = None

DESKTOP_STATIC_DIR = (DESKTOP_DATA_DIR / "static").resolve()
STATICFILES_DIRS = (
    [p for p in [DESKTOP_STATIC_DIR, _BUNDLED_STATIC_DIR, BASE_DIR / "static"] if p]
    if (IS_FROZEN or DESKTOP_MODE)
    else [BASE_DIR / "static"]
)
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if (DEBUG or DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS)
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# ---------------- GOOGLE SMS (Verified SMS / RCS Gateway) ----------------
# Note: in most real deployments, Verified SMS is accessed through partner gateways.
# sms_center.sms_service supports overriding the API endpoint via GOOGLE_SMS_API_URL.
GOOGLE_SMS_API_KEY = (os.getenv("GOOGLE_SMS_API_KEY") or "").strip()
GOOGLE_SMS_SENDER_ID = (os.getenv("GOOGLE_SMS_SENDER_ID") or "").strip()
GOOGLE_SMS_API_URL = (os.getenv("GOOGLE_SMS_API_URL") or "").strip()

# Back-compat for older Django/settings usage.
STATICFILES_STORAGE = STORAGES["staticfiles"]["BACKEND"]

# For desktop/offline-first builds (DEBUG=False) and local runserver, still serve static via finders.
WHITENOISE_USE_FINDERS = bool(DEBUG or DESKTOP_MODE or RUNNING_RUNSERVER)

MEDIA_URL = "/media/"
MEDIA_ROOT = DESKTOP_DATA_DIR / "media"
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

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
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "saas_core.permissions.IsTenantUser",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("DRF_PAGE_SIZE", "20")),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Universal Billing + POS + Quick Commerce API",
    "DESCRIPTION": "Real-estate AgentFlow platform",
    "VERSION": "1.0.1",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------- OPENAI ----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------- LOGGING ----------------
_DESKTOP_LOG_PATH = (os.getenv("KP_DESKTOP_LOG_FILE") or "").strip()
if not _DESKTOP_LOG_PATH:
    _DESKTOP_LOG_PATH = str((DESKTOP_DATA_DIR / "logs" / "desktop.log").resolve())

try:
    Path(_DESKTOP_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "desktop_file_filter": {
            "()": "realstateproject.logging_filters.DesktopFileLogFilter",
        },
    },
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "desktop_file": {
            "class": "logging.FileHandler",
            "filename": _DESKTOP_LOG_PATH,
            "encoding": "utf-8",
            "formatter": "standard",
            "filters": ["desktop_file_filter"],
        },
    },
    "root": {
        "handlers": ["console"] + (["desktop_file"] if (DESKTOP_MODE or RUNNING_RUNSERVER) else []),
        "level": "INFO",
    },
    "loggers": {
        # Ensure request logs also reach the file in desktop/dev mode.
        "django.server": {
            "handlers": ["console"] + (["desktop_file"] if (DESKTOP_MODE or RUNNING_RUNSERVER) else []),
            "level": "INFO",
            "propagate": False,
        },
        # Cloud/dev ASGI servers (Daphne/Channels) use these loggers for request lines.
        "django.channels.server": {
            "handlers": ["console"] + (["desktop_file"] if (DESKTOP_MODE or RUNNING_RUNSERVER) else []),
            "level": "INFO",
            "propagate": False,
        },
        "daphne.server": {
            "handlers": ["console"] + (["desktop_file"] if (DESKTOP_MODE or RUNNING_RUNSERVER) else []),
            "level": "INFO",
            "propagate": False,
        },
    },
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
    "topmenu_links": [
        {
            "name": "Desktop Logs",
            "url": "admin:core_settings_desktoprelease_desktop_logs",
            "permissions": ["core_settings.view_desktoprelease"],
        },
    ],
    # Hide non–real-estate modules from sidebar
    "hide_apps": [
        # keep commerce hidden
        # "commerce",
        "products",
        "orders",
        "warehouse",
        "printer_config",
        "scanner_config",
        "procurement",
        "pos",
        "bank_import",
        # show billing/subscription/plans
        # "billing",
        # "subscription",
        # "plans",
        "wallet",
        "performance",
        "analytics",
        "ai_engine",
        "ai_insights",
        "ai_ocr",
        "marketing",
        "sms_center",
        "smart_khata",
        "mobileapi",
        "chatbot",
        "event_bus",
        "reports",
        "realtime",
        "commission",
        "payments",
        # "accounts",
        "core_settings",  # hide noisy config models
        "smart_bi",
        "fraud_detection",
        "portal",
        # "delivery",  # removed missing app
    ],
    "hide_models": [
        # show auth.Group
        "auth.Permission",
    ],
}

JAZZMIN_UI_TWEAKS = {
    "theme": "default",
    "navbar": "navbar-dark",
    "sidebar": "sidebar-dark-primary",
}

# ---------------- CELERY (OPTIONAL) ----------------
if DISABLE_CELERY:
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
else:
    CELERY_BROKER_URL = CELERY_BROKER_URL_ENV or REDIS_URL or "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND = CELERY_RESULT_BACKEND_ENV or REDIS_URL or "redis://127.0.0.1:6379/0"
CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ALWAYS_EAGER = DISABLE_CELERY
CELERY_TASK_EAGER_PROPAGATES = bool(RUNNING_TESTS)
CELERY_TASK_IGNORE_RESULT = DISABLE_CELERY

# Optional: daily Smart BI metric refresh (Celery Beat recommended on server deployments).
try:
    from celery.schedules import crontab

    _KAFKA_ENABLED = (os.getenv("KAFKA_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}

    CELERY_BEAT_SCHEDULE = {
        "lead_process_due_followups": {
            "task": "leads.tasks.process_due_followups_task",
            "schedule": crontab(minute="*/15"),
        },
        "lead_reassign_stale_hourly": {
            "task": "leads.tasks.reassign_stale_leads_task",
            "schedule": crontab(minute="*/20"),
        },
        "lead_send_inactive_followups_hourly": {
            "task": "leads.tasks.send_inactive_lead_followups_task",
            "schedule": crontab(minute="*/30"),
        },
        "lead_refresh_scores_hourly": {
            "task": "leads.tasks.refresh_open_lead_scores_task",
            "schedule": crontab(minute=10, hour="*"),
        },
        "voice_schedule_inactive_leads": {
            "task": "voice.tasks.schedule_inactive_lead_calls_task",
            "schedule": crontab(minute="*/30"),
        },
        "marketing_process_scheduled_campaigns": {
            "task": "marketing.tasks.process_scheduled_campaigns",
            "schedule": crontab(minute="*/10"),
        },
        "intelligence_refresh_heatmaps": {
            "task": "intelligence.tasks.refresh_demand_heatmap_task",
            "schedule": crontab(minute=20, hour="*"),
        },
        "intelligence_refresh_price_trends": {
            "task": "intelligence.tasks.refresh_price_trends_task",
            "schedule": crontab(minute=40, hour="*"),
        },
        "intelligence_refresh_investor_matches": {
            "task": "intelligence.tasks.refresh_investor_matches_task",
            "schedule": crontab(minute="*/20"),
        },
        "intelligence_notify_investor_matches": {
            "task": "intelligence.tasks.notify_pending_investor_matches_task",
            "schedule": crontab(minute="*/15"),
        },
        "intelligence_expire_premium_leads": {
            "task": "intelligence.tasks.expire_premium_leads_task",
            "schedule": crontab(minute=0, hour="*/2"),
        },
        # "central_engine_update_engine_snapshots_daily": {
        #     "task": "khataapp.tasks.update_engine_snapshots_daily",
        #     "schedule": crontab(minute=10, hour=0),
        # },
        "whatsapp_send_supplier_payment_reminders_daily": {
            "task": "whatsapp.tasks.send_supplier_payment_reminders_daily",
            "schedule": crontab(minute=30, hour=9),
        },
        "whatsapp_run_scheduled_broadcasts": {
            "task": "whatsapp.tasks.run_scheduled_broadcasts",
            "schedule": crontab(minute="*/2"),
        },
        "event_bus_flush_outbox": {
            "task": "event_bus.tasks.flush_outbox",
            "schedule": crontab(minute="*/1"),
        },
    }

    if not _KAFKA_ENABLED:
        CELERY_BEAT_SCHEDULE.pop("event_bus_flush_outbox", None)
except Exception:
    CELERY_BEAT_SCHEDULE = {}

# ---------------- SECURITY (PROD DEFAULTS) ----------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = False if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS) else (not DEBUG)
CSRF_COOKIE_SECURE = False if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS) else (not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

# Desktop stability: avoid SQLite session table churn (and native crashes observed in some Windows builds)
# by using signed cookie sessions in desktop mode.
if DESKTOP_MODE:
    SESSION_ENGINE = os.getenv("DESKTOP_SESSION_ENGINE", "django.contrib.sessions.backends.signed_cookies")
SECURE_HSTS_SECONDS = 0 if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS) else int(os.getenv("SECURE_HSTS_SECONDS", "0" if DEBUG else "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    False
    if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS)
    else (os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False" if DEBUG else "True") == "True")
)
SECURE_HSTS_PRELOAD = False if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS) else (os.getenv("SECURE_HSTS_PRELOAD", "False") == "True")
# Local dev: prevent redirecting localhost to HTTPS (Daphne dev server isn't TLS).
SECURE_SSL_REDIRECT = (
    False
    if (DESKTOP_MODE or RUNNING_RUNSERVER or RUNNING_TESTS)
    else (os.getenv("SECURE_SSL_REDIRECT", "False" if DEBUG else "True") == "True")
)
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "SAMEORIGIN")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]

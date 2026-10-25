import os
import socket
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


SECRET_KEY = env("SECRET_KEY", "dev-insecure-change-me-in-production-9f8e7d6c5b4a3210")
DEBUG = env("DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "door",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "smartdoor.urls"
WSGI_APPLICATION = "smartdoor.wsgi.application"
ASGI_APPLICATION = "smartdoor.asgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# ---- Database (Supabase PostgreSQL with automatic local SQLite fallback) ----
SQLITE_DEFAULT = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": env("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
}
DATABASES = {"default": SQLITE_DEFAULT}

_raw_db_url = (env("DATABASE_URL") or env("SUPABASE_DB_URL") or "").strip()
_is_placeholder_db = any(
    tok in _raw_db_url
    for tok in ("[YOUR-PASSWORD]", "YOUR_PASSWORD", "your-project-ref", "<password>")
)

if _raw_db_url and not _is_placeholder_db:
    try:
        import dj_database_url
        is_supabase_host = "supabase.co" in _raw_db_url or "supabase.com" in _raw_db_url
        parsed_db = dj_database_url.parse(
            _raw_db_url,
            conn_max_age=600,
            ssl_require=is_supabase_host,
        )
        # Supabase Transaction Pooler (port 6543) requires disabling server-side cursors
        parsed_db["DISABLE_SERVER_SIDE_CURSORS"] = True

        # Optional reachability check so local dev falls back cleanly if offline
        if env("SUPABASE_FALLBACK_SQLITE", "1") == "1":
            u = urlparse(_raw_db_url)
            if u.hostname:
                with socket.create_connection((u.hostname, u.port or 5432), timeout=3.0):
                    pass
        DATABASES = {"default": parsed_db}
    except Exception as _db_exc:
        if env("SUPABASE_FALLBACK_SQLITE", "1") != "1":
            raise
        print(f"[SmartDoor] DATABASE_URL unreachable ({_db_exc}); using local SQLite fallback.")

# Optional Supabase REST / PostgREST credentials
SUPABASE_URL = env("SUPABASE_URL", "")
SUPABASE_KEY = env("SUPABASE_SERVICE_ROLE_KEY") or env("SUPABASE_KEY") or env("SUPABASE_ANON_KEY") or ""

AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.vercel\.app$"] if env("CORS_ALLOW_VERCEL", "0") == "1" else []
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# ---- Smart Door AI & IoT settings ----
# AI_BACKEND: "auto" (uses insightface if installed, else opencv real vision) | "insightface" | "opencv" | "mock"
AI_BACKEND = env("AI_BACKEND", "auto")
ALLOW_MOCK_RECOGNITION = env("ALLOW_MOCK_RECOGNITION", "0") == "1"

# IOT_MODE: "demo" (virtual timer lock) | "serial" (USB PySerial to ESP32 servo) | "real" (MQTT to ESP32)
IOT_MODE = env("IOT_MODE", "demo")
SERIAL_PORT = env("SERIAL_PORT", "COM3")
SERIAL_BAUD = int(env("SERIAL_BAUD", "115200"))
MQTT_HOST = env("MQTT_HOST", "localhost")
MQTT_PORT = int(env("MQTT_PORT", "1883"))
MQTT_DEVICE_ID = env("MQTT_DEVICE_ID", "door01")
DEVICE_API_KEY = env("DEVICE_API_KEY", "esp32-shared-secret")
CAMERA_SOURCE = env("CAMERA_SOURCE", "0")
FACES_DIR = Path(env("FACES_DIR", str(BASE_DIR.parent / "data" / "faces")))

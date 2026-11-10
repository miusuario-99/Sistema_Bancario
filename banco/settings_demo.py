from .settings import *

# Configuración exclusiva para demostración.
DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# Base de datos independiente para demostración.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_demo.sqlite3",
        "TEST": {
            "NAME": BASE_DIR / "test_db_demo.sqlite3",
        },
    }
}

# Configuración HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

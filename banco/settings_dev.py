from .settings import *

# Configuración exclusiva para desarrollo.
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Base de datos SQLite independiente.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_dev.sqlite3",
        "TEST": {
            "NAME": BASE_DIR / "test_db_dev.sqlite3",
        },
    }
}

# No forzar HTTPS durante las pruebas.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

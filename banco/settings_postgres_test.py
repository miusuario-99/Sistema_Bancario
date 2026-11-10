from .settings import *

# Configuración exclusiva para pruebas locales con PostgreSQL.
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

PASSWORD_TEST = os.getenv("BANCO_APP_TEST_PASSWORD")

if not PASSWORD_TEST:
    raise RuntimeError(
        "Falta configurar BANCO_APP_TEST_PASSWORD"
    )

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "banco_concurrencia_seguridad",
        "USER": "banco_app_test",
        "PASSWORD": PASSWORD_TEST,
        "HOST": "127.0.0.1",
        "PORT": "5432",
        "CONN_MAX_AGE": 0,
        "TEST": {
            "NAME": "test_banco_concurrencia_seguridad",
        },
    }
}

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
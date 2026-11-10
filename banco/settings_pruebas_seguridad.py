from .settings import *

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db_pruebas_seguridad.sqlite3", "TEST": {"NAME": BASE_DIR / "db_pruebas_seguridad_temporal.sqlite3"}}}

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

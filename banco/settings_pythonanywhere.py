from .settings_demo import *

# Configuración exclusiva para PythonAnywhere.
DEBUG = False

ALLOWED_HOSTS = [
    "agarrafa50.pythonanywhere.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://agarrafa50.pythonanywhere.com",
]

# HTTPS y cookies seguras.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Mantener HSTS desactivado hasta verificar HTTPS.
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Archivos estáticos.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

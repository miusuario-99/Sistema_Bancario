from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Clave secreta: debe estar definida en el entorno.
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Debes definir la variable de entorno SECRET_KEY."
    )

# DEBUG:
# Si no se define la variable, se desactiva por seguridad.
DEBUG = os.getenv("DEBUG", "False").strip().lower() == "true"

# Hosts autorizados.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",")
    if host.strip()
]

# Opciones de seguridad para producción.
if not DEBUG:
    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Lax"

    # HSTS: habilitar cuando HTTPS esté correctamente configurado.
    SECURE_HSTS_SECONDS = 31536000

    # Habilitar solo si todos los subdominios usan HTTPS.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False

    # Mantener deshabilitada la precarga hasta verificar los requisitos.
    SECURE_HSTS_PRELOAD = False


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'clientes',
    'cuentas',
    'movimientos',
    'usuarios',
    'reportes',
    "auditoria.apps.AuditoriaConfig",
    # Seguridad de autenticación
    "axes",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "banco.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "banco.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "banco_db",
        "USER": "root",
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": "localhost",
        "PORT": "3306",
        "TEST": {
            "NAME": "test_concurrencia_admin_2026",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
    "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    "OPTIONS": {
        "min_length": 12,
    },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard"

LOGOUT_REDIRECT_URL = "login"

# Configuración de registros (logging)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detallado": {
            "format": (
                "{asctime} {levelname} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },
    "handlers": {
        "archivo": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "django.log",
            "encoding": "utf-8",
            "formatter": "detallado",
        },
        "consola": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "detallado",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["archivo", "consola"],
            "level": "WARNING",
            "propagate": False,
        },
        "auditoria.signals": {
            "handlers": ["archivo", "consola"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# --------------------------------------------------
# SEGURIDAD: PROTECCIÓN CONTRA INTENTOS DE ACCESO
# --------------------------------------------------

AXES_FAILURE_LIMIT = 5

AXES_COOLOFF_TIME = 15 / 60  # 15 minutos

AXES_RESET_ON_SUCCESS = True

AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]

AXES_LOCKOUT_CALLABLE = None

# --------------------------------------------------
# BACKENDS DE AUTENTICACIÓN
# --------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

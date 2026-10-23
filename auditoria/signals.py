import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .models import Auditoria


logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    try:
        Auditoria.objects.create(
            usuario=user,
            modulo="Seguridad",
            accion="Login",
            descripcion=f"Inicio de sesión de {user.username}",
        )
        logger.info(
            "Inicio de sesión registrado para el usuario %s.",
            user.username,
        )
    except Exception:
        logger.exception(
            "Error al registrar el inicio de sesión."
        )


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    try:
        Auditoria.objects.create(
            usuario=user,
            modulo="Seguridad",
            accion="Logout",
            descripcion=(
                f"Cierre de sesión de "
                f"{user.username if user else 'Sistema'}"
            ),
        )
        logger.info(
            "Cierre de sesión registrado para el usuario %s.",
            user.username if user else "Sistema",
        )
    except Exception:
        logger.exception(
            "Error al registrar el cierre de sesión."
        )


@receiver(user_login_failed)
def registrar_login_fallido(
    sender, credentials, request, **kwargs
):
    try:
        # Registrar el identificador, nunca la contraseña.
        usuario_intentado = (
            credentials.get("username")
            or credentials.get("email")
            or "No identificado"
        )

        Auditoria.objects.create(
            usuario=None,
            modulo="Seguridad",
            accion="Login fallido",
            descripcion=(
                "Intento de inicio de sesión fallido "
                f"para el usuario: {usuario_intentado}"
            ),
        )

        logger.warning(
            "Intento de inicio de sesión fallido "
            "para el usuario: %s.",
            usuario_intentado,
        )
    except Exception:
        logger.exception(
            "Error al registrar el intento de inicio de sesión fallido."
        )
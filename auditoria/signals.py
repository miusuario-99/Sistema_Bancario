print(">>> signals.py cargado <<<")

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import Auditoria


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):

    print("===================================")
    print(">>> LOGIN DETECTADO <<<")
    print("Usuario:", user)
    print("===================================")

    try:
        Auditoria.objects.create(
            usuario=user,
            modulo="Seguridad",
            accion="Login",
            descripcion=f"Inicio de sesión de {user.username}"
        )
        print(">>> AUDITORIA LOGIN GUARDADA <<<")

    except Exception as e:
        print("ERROR:", e)


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):

    print(">>> LOGOUT DETECTADO <<<")

    try:
        Auditoria.objects.create(
            usuario=user,
            modulo="Seguridad",
            accion="Logout",
            descripcion=f"Cierre de sesión de {user.username if user else 'Sistema'}"
        )
        print(">>> AUDITORIA LOGOUT GUARDADA <<<")

    except Exception as e:
        print("ERROR:", e)
    
    
from .models import Auditoria


def registrar_auditoria(request, modulo, accion, descripcion=""):

    Auditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        modulo=modulo,
        accion=accion,
        descripcion=descripcion
    )
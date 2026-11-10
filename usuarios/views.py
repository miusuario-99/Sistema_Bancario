from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UsuarioForm
from .decorators import grupos_permitidos
from django.db import transaction, connection
from django.contrib.auth.models import User, Group


@grupos_permitidos("Administrador")
def lista_usuarios(request):
    usuarios = User.objects.all().order_by("username")

    return render(
        request,
        "usuarios/lista.html",
        {"usuarios": usuarios},
    )


@grupos_permitidos("Administrador")
def crear_usuario(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save()

            messages.success(
                request,
                f"El usuario {usuario.username} fue creado correctamente.",
            )

            return redirect("lista_usuarios")
    else:
        form = UsuarioForm()

    return render(request, "usuarios/crear.html", {"form": form})


@grupos_permitidos("Administrador")
def cambiar_estado_usuario(request, usuario_id):

    if request.method != "POST":
        return redirect("lista_usuarios")

    with transaction.atomic():

        # Bloqueo común para serializar las operaciones
        grupo_admin = Group.objects.select_for_update().get(
            name="Administrador"
        )

        usuario = get_object_or_404(
            User,
            pk=usuario_id
        )

        if usuario == request.user:
            messages.error(
                request,
                "No puedes desactivar tu propia cuenta.",
            )
            return redirect("lista_usuarios")

        es_administrador = usuario.groups.filter(
            name="Administrador"
        ).exists()

        if es_administrador and usuario.is_active:

            administradores_activos = User.objects.filter(
                groups__name="Administrador",
                is_active=True,
            ).distinct().count()

            if administradores_activos <= 1:
                messages.error(
                    request,
                    "No puedes desactivar al último administrador activo.",
                )
                return redirect("lista_usuarios")

        usuario.is_active = not usuario.is_active

        usuario.save(update_fields=["is_active"])

    estado = "activado" if usuario.is_active else "desactivado"

    messages.success(
        request,
        f"El usuario {usuario.username} fue {estado} correctamente.",
    )

    return redirect("lista_usuarios")
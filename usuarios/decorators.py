from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def grupos_permitidos(*grupos):

    def decorador(vista):

        @wraps(vista)
        @login_required
        def wrapper(request, *args, **kwargs):

            # Permitir acceso a los superusuarios
            if request.user.is_superuser:
                return vista(request, *args, **kwargs)

            # Verificar pertenencia al grupo autorizado
            if request.user.groups.filter(
                name__in=grupos
            ).exists():

                return vista(
                    request,
                    *args,
                    **kwargs
                )

            raise PermissionDenied

        return wrapper

    return decorador
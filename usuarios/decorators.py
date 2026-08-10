from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def grupos_permitidos(*grupos):

    def decorador(vista):

        @wraps(vista)
        @login_required
        def wrapper(request, *args, **kwargs):

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
from django import template

register = template.Library()


@register.filter
def tiene_grupo(usuario, nombre_grupo):
    if not usuario or not usuario.is_authenticated:
        return False

    return usuario.groups.filter(
        name=nombre_grupo
    ).exists()
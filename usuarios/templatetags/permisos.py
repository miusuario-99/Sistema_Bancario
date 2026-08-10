from django import template

register = template.Library()

@register.filter
def tiene_grupo(usuario, nombre_grupo):
    return usuario.groups.filter(name=nombre_grupo).exists()
from django.urls import path
from . import views

urlpatterns = [
    path("", views.lista_usuarios, name="lista_usuarios"),
    path("crear/", views.crear_usuario, name="crear_usuario"),
    path(
        "<int:usuario_id>/cambiar-estado/",
        views.cambiar_estado_usuario,
        name="cambiar_estado_usuario",
    ),
]
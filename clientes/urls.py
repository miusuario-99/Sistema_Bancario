from django.urls import path
from . import views

urlpatterns = [

    path("", views.lista_clientes, name="lista_clientes"),

    path("nuevo/", views.nuevo_cliente, name="nuevo_cliente"),

    path("editar/<int:id>/", views.editar_cliente, name="editar_cliente"),

    path("eliminar/<int:id>/", views.eliminar_cliente, name="eliminar_cliente"),
    path("excel/", views.exportar_clientes_excel, name="clientes_excel",),
    path("exportar/pdf/", views.exportar_clientes_pdf, name="clientes_pdf"),
]
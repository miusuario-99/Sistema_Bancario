from django.urls import path
from . import views


urlpatterns = [

    path(
        "",
        views.lista_cuentas,
        name="lista_cuentas"
    ),

    path(
        "nueva/",
        views.nueva_cuenta,
        name="nueva_cuenta"
    ),

    path(
        "editar/<int:id>/",
        views.editar_cuenta,
        name="editar_cuenta"
    ),

    path(
        "eliminar/<int:id>/",
        views.eliminar_cuenta,
        name="eliminar_cuenta"
    ),

    path(
        "exportar/pdf/",
        views.exportar_cuentas_pdf,
        name="cuentas_pdf"
    ),

    path(
        "exportar/excel/",
        views.exportar_cuentas_excel,
        name="cuentas_excel"
    ),
]
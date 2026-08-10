from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.lista_auditoria,
        name="lista_auditoria"
    ),

    path(
        "pdf/",
        views.exportar_auditoria_pdf,
        name="auditoria_pdf"
    ),
    
    path(
        "excel/",
        views.exportar_auditoria_excel,
        name="auditoria_excel"
    ),

]
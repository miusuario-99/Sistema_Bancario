from django.urls import path
from . import views

urlpatterns = [
    path('deposito/', views.deposito, name='deposito'),
    path('retiro/', views.retiro, name='retiro'),
    path('transferencia/', views.transferencia, name='transferencia'),
    path('historial/', views.historial, name='historial'),
    path("reporte/pdf/", views.reporte_movimientos_pdf, name="reporte_movimientos_pdf",),
    path("reporte/excel/", views.reporte_movimientos_excel, name="reporte_movimientos_excel",
    ),    
]
from django.urls import path
from . import views

from .views import (
    reporte_dashboard_pdf,
    reporte_dashboard_excel,
    reporte_clientes_pdf,
    reporte_cuentas_pdf,
    reporte_movimientos_pdf,
    reporte_movimientos_excel,
    reporte_cuentas_excel,
    reporte_clientes_excel,
)


urlpatterns = [

    # ============================
    # REPORTES
    # ============================

    path(
        "",
        views.index,
        name="reportes"
    ),

    # ============================
    # DASHBOARD
    # ============================

    path(
        "dashboard/pdf/",
        reporte_dashboard_pdf,
        name="dashboard_pdf"
    ),

    path(
        "dashboard/excel/",
        reporte_dashboard_excel,
        name="dashboard_excel"
    ),

    # ============================
    # CLIENTES
    # ============================

    path(
        "clientes/pdf/",
        reporte_clientes_pdf,
        name="clientes_pdf"
    ),

    path(
        "clientes/excel/",
        reporte_clientes_excel,
        name="reporte_clientes_excel"
    ),

    # ============================
    # CUENTAS
    # ============================

    path(
        "cuentas/pdf/",
        reporte_cuentas_pdf,
        name="cuentas_pdf"
    ),

    path(
        "cuentas/excel/",
        reporte_cuentas_excel,
        name="reporte_cuentas_excel"
    ),

    # ============================
    # MOVIMIENTOS
    # ============================

    path(
        "movimientos/pdf/",
        reporte_movimientos_pdf,
        name="movimientos_pdf"
    ),

    path(
        "movimientos/excel/",
        reporte_movimientos_excel,
        name="reporte_movimientos_excel"
    ),
]
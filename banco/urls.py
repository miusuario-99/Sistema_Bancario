from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(
            template_name="registration/login.html"), name="login",),
    path("logout/", auth_views.LogoutView.as_view(), name="logout",),
    path("", views.dashboard, name="dashboard"),
    path("movimientos/", include("movimientos.urls")),
    path("clientes/", include("clientes.urls")),
    path("estado-cuenta/", views.estado_cuenta, name="estado_cuenta"),    
    path("estado-cuenta/pdf/<int:cuenta_id>/", views.estado_cuenta_pdf, 
        name="estado_cuenta_pdf",),
    path("cuentas/", include("cuentas.urls")),
    path("reportes/", include("reportes.urls")),
    path("auditoria/", include("auditoria.urls")),
]
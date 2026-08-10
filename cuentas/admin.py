from django.contrib import admin
from .models import Cuenta


@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):

    list_display = (
        'numero_cuenta',
        'cliente',
        'tipo_cuenta',
        'saldo',
        'estado',
    )

    search_fields = (
        'numero_cuenta',
        'cliente__nombres',
        'cliente__apellidos',
    )

    list_filter = (
        'tipo_cuenta',
        'estado',
    )

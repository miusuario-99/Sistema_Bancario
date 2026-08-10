from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'dni',
        'nombres',
        'apellidos',
        'telefono',
        'estado',
    )

    search_fields = (
        'dni',
        'nombres',
        'apellidos',
    )

    list_filter = (
        'estado',
    )

    ordering = (
        'apellidos',
        'nombres',
    )

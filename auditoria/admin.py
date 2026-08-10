from django.contrib import admin
from .models import Auditoria


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):

    list_display = (
        "fecha",
        "usuario",
        "modulo",
        "accion",
    )

    list_filter = (
        "modulo",
        "usuario",
        "fecha",
    )

    search_fields = (
        "usuario__username",
        "accion",
        "descripcion",
    )

    ordering = ("-fecha",)

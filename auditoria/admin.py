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

    # Impedir crear registros manualmente desde el panel
    def has_add_permission(self, request):
        return False

    # Impedir modificar registros existentes
    def has_change_permission(self, request, obj=None):
        return False

    # Impedir eliminar registros
    def has_delete_permission(self, request, obj=None):
        return False
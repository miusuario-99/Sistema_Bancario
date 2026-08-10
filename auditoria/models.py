from django.db import models
from django.contrib.auth.models import User


class Auditoria(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    modulo = models.CharField(
        max_length=50
    )

    accion = models.CharField(
        max_length=200
    )

    descripcion = models.TextField(
        blank=True
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Auditoría"
        verbose_name_plural = "Auditorías"

    def __str__(self):
        return f"{self.fecha:%d/%m/%Y %H:%M} - {self.usuario} - {self.accion}"

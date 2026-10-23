from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class AuditoriaQuerySet(models.QuerySet):

    def update(self, **kwargs):
        raise ValidationError(
            "Los registros de auditoría no se pueden modificar."
        )

    def delete(self):
        raise ValidationError(
            "Los registros de auditoría no se pueden eliminar."
        )


class Auditoria(models.Model):

    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    modulo = models.CharField(max_length=50)

    accion = models.CharField(max_length=200)

    descripcion = models.TextField(blank=True)

    fecha = models.DateTimeField(auto_now_add=True)

    objects = AuditoriaQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Auditoría"
        verbose_name_plural = "Auditorías"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "Los registros de auditoría no se pueden modificar."
            )

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Los registros de auditoría no se pueden eliminar."
        )

    def __str__(self):
        return (
            f"{self.fecha:%d/%m/%Y %H:%M} - "
            f"{self.usuario} - {self.accion}"
        )
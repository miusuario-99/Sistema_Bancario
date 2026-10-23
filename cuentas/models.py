from django.db import models
from django.db.models import Q
from clientes.models import Cliente


class Cuenta(models.Model):

    TIPO_CUENTA = [
        ("AH", "Ahorros"),
        ("CC", "Cuenta Corriente"),
    ]

    ESTADO = [
        ("A", "Activa"),
        ("I", "Inactiva"),
    ]

    numero_cuenta = models.CharField(
        max_length=10,
        unique=True
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="cuentas"
    )

    tipo_cuenta = models.CharField(
        max_length=2,
        choices=TIPO_CUENTA
    )

    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    fecha_apertura = models.DateField(
        auto_now_add=True
    )

    estado = models.CharField(
        max_length=1,
        choices=ESTADO,
        default="A"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(saldo__gte=0),
                name="cuenta_saldo_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.numero_cuenta} - {self.cliente}"

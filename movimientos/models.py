from django.db import models
from cuentas.models import Cuenta


class Movimiento(models.Model):

    TIPO = [
        ('D', 'Deposito'),
        ('R', 'Retiro'),
        ('T', 'Transferencia'),
    ]

    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=1, choices=TIPO)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=12, decimal_places=2,
    default=0)
    saldo_actual = models.DecimalField(max_digits=12, decimal_places=2,
    default=0)
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.cuenta.numero_cuenta} - {self.get_tipo_display()} - S/. {self.monto}"

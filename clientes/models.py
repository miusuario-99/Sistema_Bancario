from django.db import models
from django.core.validators import RegexValidator
from django.db.models.functions import Lower

class Cliente(models.Model):
    ESTADO = [
        ('A', 'Activo'),
        ('I', 'Inactivo'),
    ]

    dni = models.CharField(
    max_length=8,
    unique=True,
    validators=[
        RegexValidator(
            regex=r'^\d{8}$',
            message="El DNI debe contener exactamente 8 dígitos numéricos.",
        )
    ],
)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(
    max_length=9,
    validators=[
        RegexValidator(
            regex=r'^9\d{8}$',
            message="El teléfono debe contener 9 dígitos y comenzar con 9.",
        )
    ],
)
    correo = models.EmailField()
    estado = models.CharField(max_length=1, choices=ESTADO, default='A')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['apellidos', 'nombres']
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

        constraints = [
            models.UniqueConstraint(
                Lower('correo'),
                name='unique_correo_cliente_lower'
            )
        ]

    def __str__(self):
        return f"{self.dni} - {self.nombres} {self.apellidos}"

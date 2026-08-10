from django.db import models


class Cliente(models.Model):
    ESTADO = [
        ('A', 'Activo'),
        ('I', 'Inactivo'),
    ]

    dni = models.CharField(max_length=8, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField()
    estado = models.CharField(max_length=1, choices=ESTADO, default='A')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['apellidos', 'nombres']
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.dni} - {self.nombres} {self.apellidos}"

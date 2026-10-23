from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from clientes.models import Cliente
from movimientos.models import Movimiento
from .models import Cuenta


class SeguridadCuentasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.grupo_admin, _ = Group.objects.get_or_create(
            name="Administrador"
        )
        cls.grupo_supervisor, _ = Group.objects.get_or_create(
            name="Supervisor"
        )
        cls.grupo_cajero, _ = Group.objects.get_or_create(
            name="Cajero"
        )

        cls.admin = User.objects.create_user(
            username="admin_cuentas_prueba",
            password="PruebaSegura123"
        )
        cls.admin.groups.add(cls.grupo_admin)

        cls.supervisor = User.objects.create_user(
            username="supervisor_cuentas_prueba",
            password="PruebaSegura123"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        cls.cajero = User.objects.create_user(
            username="cajero_cuentas_prueba",
            password="PruebaSegura123"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.cliente = Cliente.objects.create(
            dni="77777777",
            nombres="Cliente",
            apellidos="Prueba Cuentas",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="cuentas_prueba@example.com",
            estado="A"
        )

        cls.cuenta = Cuenta.objects.create(
            numero_cuenta="CTEST00001",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("1000.00"),
            estado="A"
        )

    def test_cuenta_tiene_saldo_inicial_correcto(self):
        self.assertEqual(self.cuenta.saldo, Decimal("1000.00"))

    def test_cuenta_esta_asociada_al_cliente(self):
        self.assertEqual(self.cuenta.cliente, self.cliente)

    def test_numero_cuenta_es_unico(self):
        with self.assertRaises(Exception):
            Cuenta.objects.create(
                numero_cuenta="CTEST00001",
                cliente=self.cliente,
                tipo_cuenta="AH",
                saldo=Decimal("500.00"),
                estado="A"
            )

    def test_cuenta_activa_se_guarda_correctamente(self):
        self.assertEqual(self.cuenta.estado, "A")

    def test_cuenta_inactiva_se_guarda_correctamente(self):
        self.cuenta.estado = "I"
        self.cuenta.save()
        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.estado, "I")

    def test_cuenta_usa_tipo_ahorros(self):
        self.assertEqual(self.cuenta.tipo_cuenta, "AH")

    def test_admin_no_puede_eliminar_cuenta_con_movimientos(self):
        # Registrar un movimiento en la cuenta de prueba
        Movimiento.objects.create(
            cuenta=self.cuenta,
            tipo="D",
            monto=Decimal("100.00"),
            saldo_anterior=Decimal("1000.00"),
            saldo_actual=Decimal("1100.00"),
            descripcion="Depósito de prueba"
        )

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("eliminar_cuenta", args=[self.cuenta.id])
        )

        # La vista debe redirigir a la lista de cuentas
        self.assertEqual(respuesta.status_code, 302)

        # La cuenta debe seguir existiendo
        self.assertTrue(
            Cuenta.objects.filter(id=self.cuenta.id).exists()
        )

        # El movimiento también debe conservarse
        self.assertTrue(
            Movimiento.objects.filter(cuenta=self.cuenta).exists()
        )

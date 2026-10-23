from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Cliente
from cuentas.models import Cuenta

class SeguridadClientesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Grupos del sistema
        cls.grupo_admin, _ = Group.objects.get_or_create(
            name="Administrador"
        )
        cls.grupo_supervisor, _ = Group.objects.get_or_create(
            name="Supervisor"
        )
        cls.grupo_cajero, _ = Group.objects.get_or_create(
            name="Cajero"
        )

        # Usuarios de prueba
        cls.admin = User.objects.create_user(
            username="admin_clientes_prueba",
            password="PruebaSegura123"
        )
        cls.admin.groups.add(cls.grupo_admin)

        cls.supervisor = User.objects.create_user(
            username="supervisor_clientes_prueba",
            password="PruebaSegura123"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        cls.cajero = User.objects.create_user(
            username="cajero_clientes_prueba",
            password="PruebaSegura123"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        # Cliente de prueba
        cls.cliente = Cliente.objects.create(
            dni="88888888",
            nombres="Cliente",
            apellidos="Prueba",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="cliente_prueba@example.com",
            estado="A"
        )

    def test_cajero_puede_listar_clientes(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("lista_clientes"))
        self.assertEqual(respuesta.status_code, 200)

    def test_supervisor_puede_listar_clientes(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("lista_clientes"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_puede_abrir_formulario_nuevo(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("nuevo_cliente"))
        self.assertEqual(respuesta.status_code, 200)

    def test_supervisor_no_puede_registrar_clientes(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("nuevo_cliente"))
        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_editar_clientes(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(
            reverse("editar_cliente", args=[self.cliente.id])
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_supervisor_no_puede_editar_clientes(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(
            reverse("editar_cliente", args=[self.cliente.id])
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_eliminar_clientes(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(
            Cliente.objects.filter(id=self.cliente.id).exists()
        )

    def test_supervisor_no_puede_eliminar_clientes(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(
            Cliente.objects.filter(id=self.cliente.id).exists()
        )
    def test_admin_no_puede_eliminar_cliente_con_cuentas(self):
        # Crear una cuenta bancaria asociada al cliente de prueba
        cuenta = Cuenta.objects.create(
            numero_cuenta="9999999999",
            cliente=self.cliente,
            tipo_cuenta="AH"
        )

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        # La vista debe redirigir mostrando el mensaje de error
        self.assertEqual(respuesta.status_code, 302)

        # El cliente y su cuenta deben seguir existiendo
        self.assertTrue(
            Cliente.objects.filter(id=self.cliente.id).exists()
        )
        self.assertTrue(
            Cuenta.objects.filter(id=cuenta.id).exists()
        )

    def test_cajero_puede_exportar_excel(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("clientes_excel"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "spreadsheetml",
            respuesta["Content-Type"]
        )

    def test_supervisor_puede_exportar_pdf(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("clientes_pdf"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf"
        )

    def test_usuario_sin_sesion_no_puede_listar(self):
        respuesta = self.client.get(reverse("lista_clientes"))
        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_puede_eliminar(self):
        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            Cliente.objects.filter(id=self.cliente.id).exists()
        )

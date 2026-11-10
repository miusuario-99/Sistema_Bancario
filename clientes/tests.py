from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Cliente
from cuentas.models import Cuenta
from auditoria.models import Auditoria
from django.core.exceptions import ValidationError
from .forms import ClienteForm

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

    def test_admin_desactiva_cliente_sin_eliminarlo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        # La vista debe redirigir a la lista de clientes.
        self.assertEqual(respuesta.status_code, 302)

        # El registro debe seguir existiendo.
        self.assertTrue(
            Cliente.objects.filter(id=self.cliente.id).exists()
        )

        # El estado debe cambiar de Activo a Inactivo.
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.estado, "I")

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

    def test_admin_desactivar_cliente_registra_auditoria(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("eliminar_cliente", args=[self.cliente.id])
        )

        self.assertEqual(respuesta.status_code, 302)

        # Verificar que el cliente se conservó.
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.estado, "I")

        # Verificar que la operación quedó registrada.
        registro = Auditoria.objects.filter(
            usuario=self.admin,
            modulo="Clientes",
            accion="Desactivar",
            descripcion=(
                f"Cliente: {self.cliente.dni} - "
                f"{self.cliente.nombres} {self.cliente.apellidos}"
            ),
        ).first()

        self.assertIsNotNone(
            registro,
            "No se encontró la auditoría de desactivación."
        )

class ValidacionDNIClientesTests(TestCase):

    def test_dni_con_ocho_digitos_es_valido(self):
        cliente = Cliente(
            dni="12345678",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="juan@example.com",
        )

        cliente.full_clean()

    def test_dni_con_siete_digitos_es_invalido(self):
        cliente = Cliente(
            dni="1234567",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="juan@example.com",
        )

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_dni_con_nueve_digitos_es_invalido(self):
        cliente = Cliente(
            dni="123456789",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="juan@example.com",
        )

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_dni_con_letras_es_invalido(self):
        cliente = Cliente(
            dni="1234ABCD",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="999999999",
            correo="juan@example.com",
        )

        with self.assertRaises(ValidationError):
            cliente.full_clean()

class ValidacionTelefonoClientesTests(TestCase):

    def crear_cliente(self, telefono):
        return Cliente(
            dni="12345678",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono=telefono,
            correo="juan@example.com",
        )

    def test_telefono_valido(self):
        cliente = self.crear_cliente("987654321")
        cliente.full_clean()

    def test_telefono_con_ocho_digitos(self):
        cliente = self.crear_cliente("98765432")

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_telefono_con_diez_digitos(self):
        cliente = self.crear_cliente("9876543210")

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_telefono_que_no_comienza_con_nueve(self):
        cliente = self.crear_cliente("887654321")

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_telefono_con_letras(self):
        cliente = self.crear_cliente("98765ABCD")

        with self.assertRaises(ValidationError):
            cliente.full_clean()

    def test_dos_clientes_pueden_compartir_telefono(self):
        cliente1 = self.crear_cliente("987654321")
        cliente1.full_clean()
        cliente1.save()

        cliente2 = Cliente(
            dni="87654321",
            nombres="Maria",
            apellidos="Lopez",
            fecha_nacimiento="1992-05-20",
            direccion="Direccion de prueba",
            telefono="987654321",
            correo="maria@example.com",
        )

        cliente2.full_clean()
        cliente2.save()

        self.assertEqual(
            Cliente.objects.filter(telefono="987654321").count(),
            2
        )

class ValidacionCorreoClientesTests(TestCase):

    def crear_cliente(self, correo):
        return Cliente(
            dni="12345678",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="987654321",
            correo=correo,
        )

    def test_correo_nuevo_es_valido(self):
        form = ClienteForm(data={
            "dni": "12345678",
            "nombres": "Juan",
            "apellidos": "Perez",
            "fecha_nacimiento": "1990-01-15",
            "direccion": "Direccion de prueba",
            "telefono": "987654321",
            "correo": "nuevo@example.com",
            "estado": "A",
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_correo_duplicado_es_invalido(self):
        cliente = self.crear_cliente("juan@example.com")
        cliente.save()

        form = ClienteForm(data={
            "dni": "12345679",
            "nombres": "Pedro",
            "apellidos": "Lopez",
            "fecha_nacimiento": "1990-01-15",
            "direccion": "Direccion de prueba",
            "telefono": "987654322",
            "correo": "juan@example.com",
            "estado": "A",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_correo_duplicado_en_mayusculas_es_invalido(self):
        cliente = self.crear_cliente("juan@example.com")
        cliente.save()

        form = ClienteForm(data={
            "dni": "12345679",
            "nombres": "Pedro",
            "apellidos": "Lopez",
            "fecha_nacimiento": "1990-01-15",
            "direccion": "Direccion de prueba",
            "telefono": "987654322",
            "correo": "JUAN@EXAMPLE.COM",
            "estado": "A",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

class EdicionCorreoClienteTests(TestCase):

    def setUp(self):
        self.cliente1 = Cliente.objects.create(
            dni="12345678",
            nombres="Juan",
            apellidos="Perez",
            fecha_nacimiento="1990-01-15",
            direccion="Lima",
            telefono="987654321",
            correo="juan@example.com",
            estado="A",
        )

        self.cliente2 = Cliente.objects.create(
            dni="87654321",
            nombres="Maria",
            apellidos="Lopez",
            fecha_nacimiento="1992-05-20",
            direccion="Lima",
            telefono="912345678",
            correo="maria@example.com",
            estado="A",
        )

    def test_editar_cliente_con_su_propio_correo(self):
        form = ClienteForm(
            data={
                "dni": "12345678",
                "nombres": "Juan Carlos",
                "apellidos": "Perez",
                "fecha_nacimiento": "1990-01-15",
                "direccion": "Lima",
                "telefono": "987654321",
                "correo": "juan@example.com",
                "estado": "A",
            },
            instance=self.cliente1,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_editar_cliente_con_correo_de_otro_cliente(self):
        form = ClienteForm(
            data={
                "dni": "12345678",
                "nombres": "Juan",
                "apellidos": "Perez",
                "fecha_nacimiento": "1990-01-15",
                "direccion": "Lima",
                "telefono": "987654321",
                "correo": "maria@example.com",
                "estado": "A",
            },
            instance=self.cliente1,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_editar_cliente_con_correo_duplicado_en_mayusculas(self):
        form = ClienteForm(
            data={
                "dni": "12345678",
                "nombres": "Juan",
                "apellidos": "Perez",
                "fecha_nacimiento": "1990-01-15",
                "direccion": "Lima",
                "telefono": "987654321",
                "correo": "MARIA@EXAMPLE.COM",
                "estado": "A",
            },
            instance=self.cliente1,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

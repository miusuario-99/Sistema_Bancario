from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Auditoria
from django.contrib.admin.sites import AdminSite
from .admin import AuditoriaAdmin

class SeguridadAuditoriaTests(TestCase):

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
            username="admin_auditoria_prueba",
            password="PruebaSegura123"
        )
        cls.admin.groups.add(cls.grupo_admin)

        cls.supervisor = User.objects.create_user(
            username="supervisor_auditoria_prueba",
            password="PruebaSegura123"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        cls.cajero = User.objects.create_user(
            username="cajero_auditoria_prueba",
            password="PruebaSegura123"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.registro = Auditoria.objects.create(
            usuario=cls.admin,
            modulo="Clientes",
            accion="Crear cliente",
            descripcion="Registro de prueba"
        )

    def test_administrador_puede_consultar_auditoria(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("lista_auditoria"))

        self.assertEqual(respuesta.status_code, 200)

    def test_supervisor_puede_consultar_auditoria(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("lista_auditoria"))

        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_no_puede_consultar_auditoria(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("lista_auditoria"))

        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_exportar_pdf(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("auditoria_pdf"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf"
        )

    def test_supervisor_puede_exportar_pdf(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("auditoria_pdf"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf"
        )

    def test_cajero_no_puede_exportar_pdf(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("auditoria_pdf"))

        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_exportar_excel(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("auditoria_excel"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "spreadsheetml",
            respuesta["Content-Type"]
        )

    def test_supervisor_puede_exportar_excel(self):
        self.client.force_login(self.supervisor)
        respuesta = self.client.get(reverse("auditoria_excel"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            "spreadsheetml",
            respuesta["Content-Type"]
        )

    def test_cajero_no_puede_exportar_excel(self):
        self.client.force_login(self.cajero)
        respuesta = self.client.get(reverse("auditoria_excel"))

        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_sin_sesion_no_puede_consultar(self):
        respuesta = self.client.get(reverse("lista_auditoria"))

        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_puede_exportar_pdf(self):
        respuesta = self.client.get(reverse("auditoria_pdf"))

        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_puede_exportar_excel(self):
        respuesta = self.client.get(reverse("auditoria_excel"))

        self.assertEqual(respuesta.status_code, 302)

    def test_registro_conserva_sus_datos(self):
        registro = Auditoria.objects.get(
            pk=self.registro.pk
        )

        self.assertEqual(registro.usuario, self.admin)
        self.assertEqual(registro.modulo, "Clientes")
        self.assertEqual(registro.accion, "Crear cliente")
        self.assertEqual(
            registro.descripcion,
            "Registro de prueba"
        )
        self.assertIsNotNone(registro.fecha)

class AuditoriaAdminProteccionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.usuario_admin = User.objects.create_superuser(
            username="superadmin_auditoria",
            email="superadmin@example.com",
            password="PruebaSegura123"
        )

        cls.registro = Auditoria.objects.create(
            usuario=cls.usuario_admin,
            modulo="Clientes",
            accion="Crear cliente",
            descripcion="Registro de prueba para Admin"
        )

    def setUp(self):
        self.site = AdminSite()
        self.admin_auditoria = AuditoriaAdmin(
            Auditoria,
            self.site
        )

    def test_no_permite_agregar_registros(self):
        permitido = self.admin_auditoria.has_add_permission(
            self.usuario_admin
        )
        self.assertFalse(permitido)

    def test_no_permite_modificar_registros(self):
        permitido = self.admin_auditoria.has_change_permission(
            self.usuario_admin,
            self.registro
        )
        self.assertFalse(permitido)

    def test_no_permite_eliminar_registros(self):
        permitido = self.admin_auditoria.has_delete_permission(
            self.usuario_admin,
            self.registro
        )
        self.assertFalse(permitido)

class AuditoriaModeloProteccionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(
            username="usuario_prueba_proteccion",
            password="PruebaSegura123"
        )

        cls.registro = Auditoria.objects.create(
            usuario=cls.usuario,
            modulo="Prueba",
            accion="Verificar proteccion",
            descripcion="Registro temporal de prueba"
        )

    def test_permite_crear_registros(self):
        registro = Auditoria.objects.create(
            usuario=self.usuario,
            modulo="Prueba",
            accion="Nueva accion"
        )
        self.assertIsNotNone(registro.pk)

    def test_bloquea_modificacion(self):
        self.registro.accion = "Intento de cambio"

        with self.assertRaises(Exception):
            self.registro.save()

    def test_bloquea_eliminacion_individual(self):
        with self.assertRaises(Exception):
            self.registro.delete()

    def test_bloquea_actualizacion_masiva(self):
        with self.assertRaises(Exception):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).update(accion="Intento de cambio")

    def test_bloquea_eliminacion_masiva(self):
        with self.assertRaises(Exception):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).delete()

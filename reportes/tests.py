from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group


User = get_user_model()


class PermisosReportesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear grupos autorizados
        cls.grupo_admin = Group.objects.create(
            name="Administrador"
        )

        cls.grupo_supervisor = Group.objects.create(
            name="Supervisor"
        )

        # Crear administrador
        cls.admin = User.objects.create_user(
            username="admin_reportes",
            password="PruebaSegura123!"
        )
        cls.admin.groups.add(cls.grupo_admin)

        # Crear supervisor
        cls.supervisor = User.objects.create_user(
            username="supervisor_reportes",
            password="PruebaSegura123!"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        # Crear usuario sin permisos
        cls.usuario = User.objects.create_user(
            username="usuario_reportes",
            password="PruebaSegura123!"
        )

    def test_usuario_no_autenticado_es_redirigido(self):
        respuesta = self.client.get(
            reverse("reportes")
        )

        self.assertEqual(
            respuesta.status_code,
            302
        )

    def test_administrador_accede_a_reportes(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("reportes")
        )

        self.assertEqual(
            respuesta.status_code,
            200
        )

    def test_usuario_sin_grupo_permitido_recibe_403(self):
        self.client.force_login(self.usuario)

        respuesta = self.client.get(
            reverse("reportes")
        )

        self.assertEqual(
            respuesta.status_code,
            403
        )

    def test_supervisor_accede_a_reportes(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.get(
            reverse("reportes")
        )

        self.assertEqual(
            respuesta.status_code,
            200
        )
class GeneracionReportesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.grupo_admin = Group.objects.create(
            name="Administrador"
        )

        cls.admin = User.objects.create_user(
            username="admin_generacion_reportes",
            password="PruebaSegura123!"
        )

        cls.admin.groups.add(cls.grupo_admin)

    def setUp(self):
        self.client.force_login(self.admin)

    def comprobar_reporte(self, nombre_url, tipo_contenido):
        respuesta = self.client.get(
            reverse(nombre_url)
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            msg=f"Falló el reporte: {nombre_url}"
        )

        self.assertTrue(
            respuesta["Content-Type"].startswith(tipo_contenido),
            msg=f"Tipo de contenido incorrecto: {nombre_url}"
        )

        self.assertIn(
            "Content-Disposition",
            respuesta,
            msg=f"Falta la cabecera de descarga: {nombre_url}"
        )

        self.assertGreater(
            len(respuesta.content),
            0,
            msg=f"El archivo está vacío: {nombre_url}"
        )

    def test_dashboard_pdf(self):
        self.comprobar_reporte(
            "dashboard_pdf",
            "application/pdf"
        )

    def test_dashboard_excel(self):
        self.comprobar_reporte(
            "dashboard_excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_clientes_pdf(self):
        self.comprobar_reporte(
            "clientes_pdf",
            "application/pdf"
        )

    def test_clientes_excel(self):
        self.comprobar_reporte(
            "reporte_clientes_excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_cuentas_pdf(self):
        self.comprobar_reporte(
            "cuentas_pdf",
            "application/pdf"
        )

    def test_cuentas_excel(self):
        self.comprobar_reporte(
            "reporte_cuentas_excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_movimientos_pdf(self):
        self.comprobar_reporte(
            "movimientos_pdf",
            "application/pdf"
        )

    def test_movimientos_excel(self):
        self.comprobar_reporte(
            "reporte_movimientos_excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
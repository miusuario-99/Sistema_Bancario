from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
from .models import Auditoria
from django.contrib.admin.sites import AdminSite
from .admin import AuditoriaAdmin
from django.core.exceptions import ValidationError

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

    def test_lista_auditoria_rechaza_fecha_inicial_invalida(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("lista_auditoria"),
            {"fecha_inicio": "fecha-invalida"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["page_obj"].object_list), 0)
        self.assertTrue(
            any(
                "fecha inicial" in mensaje.message.lower()
                for mensaje in respuesta.wsgi_request._messages
            )
        )

    def test_lista_auditoria_rechaza_fecha_final_invalida(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("lista_auditoria"),
            {"fecha_fin": "31/12/2026"}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["page_obj"].object_list), 0)
        self.assertTrue(
            any(
                "fecha final" in mensaje.message.lower()
                for mensaje in respuesta.wsgi_request._messages
            )
        )

    def test_lista_auditoria_rechaza_rango_de_fechas_invertido(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("lista_auditoria"),
            {
                "fecha_inicio": "2026-12-31",
                "fecha_fin": "2026-01-01"
            }
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["page_obj"].object_list), 0)
        self.assertTrue(
            any(
                "posterior" in mensaje.message.lower()
                for mensaje in respuesta.wsgi_request._messages
            )
        )

    def test_lista_auditoria_acepta_fechas_validas(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("lista_auditoria"),
            {
                "fecha_inicio": "2000-01-01",
                "fecha_fin": "2100-12-31"
            }
        )

        self.assertEqual(respuesta.status_code, 200)

        registros_mostrados = list(
            respuesta.context["page_obj"].object_list
        )

        self.assertGreaterEqual(len(registros_mostrados), 1)

        self.assertTrue(
            any(
                registro.pk == self.registro.pk
                for registro in registros_mostrados
            )
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

    def test_pdf_incluye_numeracion_de_paginas(self):
        from io import BytesIO
        from pypdf import PdfReader

        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("auditoria_pdf")
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf"
        )

        lector = PdfReader(BytesIO(respuesta.content))

        self.assertGreaterEqual(len(lector.pages), 1)

        texto_pdf = "\n".join(
            pagina.extract_text() or ""
            for pagina in lector.pages
        )

        self.assertIn("Pagina 1 de", texto_pdf.replace("á", "a").replace("Á", "A"))

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

    def test_excel_exporta_descripcion_como_texto(self):
        self.client.force_login(self.admin)

        Auditoria.objects.create(
            usuario=self.admin,
            modulo="Prueba",
            accion="Prueba Excel",
            descripcion="=1+1"
        )

        respuesta = self.client.get(
            reverse("auditoria_excel")
        )

        self.assertEqual(respuesta.status_code, 200)

        from io import BytesIO
        from openpyxl import load_workbook

        archivo = BytesIO(respuesta.content)
        libro = load_workbook(archivo, data_only=False)
        hoja = libro.active

        fila_prueba = next(
            fila
            for fila in hoja.iter_rows(min_row=2)
            if fila[3].value == "Prueba Excel"
        )

        celda_descripcion = fila_prueba[4]

        # El apóstrofo debe impedir que el contenido se interprete
        # como una fórmula de Excel.
        self.assertEqual(celda_descripcion.value, "'=1+1")
        self.assertNotEqual(celda_descripcion.data_type, "f")

    def test_excel_rechaza_fecha_inicio_invalida(self):
        from io import BytesIO
        from openpyxl import load_workbook

        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("auditoria_excel"),
            {"fecha_inicio": "fecha-invalida"}
        )

        self.assertEqual(respuesta.status_code, 200)

        libro = load_workbook(
            BytesIO(respuesta.content),
            read_only=True
        )
        hoja = libro.active

        # Solo debe existir la fila del encabezado.
        self.assertEqual(hoja.max_row, 1)
        libro.close()

    def test_excel_rechaza_fecha_fin_invalida(self):
        from io import BytesIO
        from openpyxl import load_workbook

        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("auditoria_excel"),
            {"fecha_fin": "31/12/2026"}
        )

        self.assertEqual(respuesta.status_code, 200)

        libro = load_workbook(
            BytesIO(respuesta.content),
            read_only=True
        )
        hoja = libro.active

        self.assertEqual(hoja.max_row, 1)
        libro.close()

    def test_excel_rechaza_rango_de_fechas_invertido(self):
        from io import BytesIO
        from openpyxl import load_workbook

        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("auditoria_excel"),
            {
                "fecha_inicio": "2026-12-31",
                "fecha_fin": "2026-01-01"
            }
        )

        self.assertEqual(respuesta.status_code, 200)

        libro = load_workbook(
            BytesIO(respuesta.content),
            read_only=True
        )
        hoja = libro.active

        self.assertEqual(hoja.max_row, 1)
        libro.close()

    def test_excel_acepta_rango_de_fechas_valido(self):
        from io import BytesIO
        from openpyxl import load_workbook

        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("auditoria_excel"),
            {
                "fecha_inicio": "2000-01-01",
                "fecha_fin": "2100-12-31"
            }
        )

        self.assertEqual(respuesta.status_code, 200)

        libro = load_workbook(
            BytesIO(respuesta.content),
            read_only=True
        )
        hoja = libro.active

        # Debe existir el encabezado y al menos un registro.
        self.assertGreaterEqual(hoja.max_row, 2)

        libro.close()

    def test_no_se_puede_modificar_registro_con_save(self):
        registro = Auditoria.objects.get(
            pk=self.registro.pk
        )

        registro.accion = "Acción modificada"

        with self.assertRaises(ValidationError):
            registro.save()

        registro.refresh_from_db()

        self.assertEqual(
            registro.accion,
            "Crear cliente"
        )

    def test_no_se_puede_modificar_con_queryset_update(self):
        with self.assertRaises(ValidationError):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).update(
                accion="Acción modificada"
            )

        registro = Auditoria.objects.get(
            pk=self.registro.pk
        )

        self.assertEqual(
            registro.accion,
            "Crear cliente"
        )

    def test_no_se_puede_eliminar_registro_individual(self):
        registro = Auditoria.objects.get(
            pk=self.registro.pk
        )

        with self.assertRaises(ValidationError):
            registro.delete()

        self.assertTrue(
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).exists()
        )

    def test_no_se_pueden_eliminar_registros_con_queryset(self):
        with self.assertRaises(ValidationError):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).delete()

        self.assertTrue(
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).exists()
        )

    def test_se_pueden_crear_nuevos_registros(self):
        registro = Auditoria.objects.create(
            usuario=self.admin,
            modulo="Seguridad",
            accion="Prueba de creación",
            descripcion="Nuevo registro de auditoría"
        )

        self.assertTrue(
            Auditoria.objects.filter(
                pk=registro.pk
            ).exists()
        )

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

        with self.assertRaises(ValidationError):
            self.registro.save()

    def test_bloquea_eliminacion_individual(self):
        with self.assertRaises(ValidationError):
            self.registro.delete()

    def test_bloquea_actualizacion_masiva(self):
        with self.assertRaises(ValidationError):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).update(
                accion="Intento de cambio"
            )

    def test_bloquea_bulk_update(self):
        self.registro.accion = "Intento de cambio masivo"

        with self.assertRaises(ValidationError):
            Auditoria.objects.bulk_update(
                [self.registro],
                ["accion"]
            )

    def test_bloquea_eliminacion_masiva(self):
        with self.assertRaises(ValidationError):
            Auditoria.objects.filter(
                pk=self.registro.pk
            ).delete()

    def test_eliminar_usuario_conserva_registro_auditoria(self):
        registro_id = self.registro.pk
        usuario_id = self.usuario.pk

        # Confirmar que el registro tiene un usuario asociado.
        self.assertEqual(
            self.registro.usuario_id,
            usuario_id
        )

        # Eliminar el usuario relacionado.
        self.usuario.delete()

        # Recuperar el registro de auditoría.
        registro = Auditoria.objects.get(pk=registro_id)

        # El registro debe conservarse.
        self.assertIsNotNone(registro)

        # La referencia al usuario debe quedar vacía.
        self.assertIsNone(registro.usuario_id)

        # Los datos de la operación deben permanecer intactos.
        self.assertEqual(
            registro.modulo,
            "Prueba"
        )
        self.assertEqual(
            registro.accion,
            "Verificar proteccion"
        )
        self.assertEqual(
            registro.descripcion,
            "Registro temporal de prueba"
        )

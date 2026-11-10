from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group
import threading
from queue import Queue
from django.test import TransactionTestCase
from django.db import close_old_connections, connection

class SeguridadUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Crear los grupos necesarios
        cls.grupo_admin, _ = Group.objects.get_or_create(
            name="Administrador"
        )
        cls.grupo_cajero, _ = Group.objects.get_or_create(
            name="Cajero"
        )

        # Crear administrador de prueba
        cls.admin = User.objects.create_user(
            username="admin_test_usuarios",
            password="PruebaSegura123!",
            email="admin_test@example.com",
        )
        cls.admin.groups.add(cls.grupo_admin)

        # Crear cajero de prueba
        cls.cajero = User.objects.create_user(
            username="cajero_test_usuarios",
            password="PruebaSegura123!",
            email="cajero_test@example.com",
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        # Usuario cuyo estado se intentará modificar
        cls.usuario_objetivo = User.objects.create_user(
            username="usuario_objetivo_test",
            password="PruebaSegura123!",
        )

    def test_administrador_puede_ver_lista(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(reverse("lista_usuarios"))

        self.assertEqual(respuesta.status_code, 200)

    def test_cajero_no_puede_ver_lista(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(reverse("lista_usuarios"))

        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_crear_usuarios(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(reverse("crear_usuario"))

        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_cambiar_estado(self):
        self.client.force_login(self.cajero)

        estado_original = self.usuario_objetivo.is_active

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[self.usuario_objetivo.pk],
            )
        )

        self.usuario_objetivo.refresh_from_db()

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(
            self.usuario_objetivo.is_active,
            estado_original,
        )

    def test_administrador_puede_desactivar_usuario(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[self.usuario_objetivo.pk],
            )
        )

        self.usuario_objetivo.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(self.usuario_objetivo.is_active)

    def test_administrador_puede_activar_usuario(self):
        self.usuario_objetivo.is_active = False
        self.usuario_objetivo.save(update_fields=["is_active"])

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[self.usuario_objetivo.pk],
            )
        )

        self.usuario_objetivo.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.usuario_objetivo.is_active)

    def test_no_se_puede_cambiar_estado_con_get(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse(
                "cambiar_estado_usuario",
                args=[self.usuario_objetivo.pk],
            )
        )

        self.usuario_objetivo.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.usuario_objetivo.is_active)

    def test_administrador_no_puede_desactivarse_a_si_mismo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[self.admin.pk],
            )
        )

        self.admin.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.admin.is_active)

    def test_administrador_puede_crear_usuario_y_asignar_grupo(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("crear_usuario"),
            {
                "username": "nuevo_usuario_test",
                "first_name": "Juan",
                "last_name": "Perez",
                "email": "juan.test@example.com",
                "groups": [self.grupo_cajero.pk],
                "password1": "PruebaSegura456!",
                "password2": "PruebaSegura456!",
            },
        )

        self.assertEqual(respuesta.status_code, 302)

        usuario = User.objects.get(username="nuevo_usuario_test")

        self.assertNotEqual(
            usuario.password,
            "PruebaSegura456!",
        )

        self.assertTrue(
            usuario.check_password("PruebaSegura456!")
        )

        self.assertEqual(usuario.first_name, "Juan")
        self.assertEqual(usuario.last_name, "Perez")
        self.assertEqual(usuario.email, "juan.test@example.com")
        self.assertTrue(
            usuario.groups.filter(name="Cajero").exists()
        )

    def test_no_crea_usuario_con_contrasenas_diferentes(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("crear_usuario"),
            {
                "username": "usuario_password_invalida",
                "first_name": "Juan",
                "last_name": "Perez",
                "email": "juan.invalido@example.com",
                "groups": [self.grupo_cajero.pk],
                "password1": "PruebaSegura456!",
                "password2": "OtraClave789!",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                username="usuario_password_invalida"
            ).exists()
        )

    def test_no_crea_usuario_con_correo_invalido(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("crear_usuario"),
            {
                "username": "usuario_email_invalido",
                "first_name": "Juan",
                "last_name": "Perez",
                "email": "correo-no-valido",
                "groups": [self.grupo_cajero.pk],
                "password1": "PruebaSegura456!",
                "password2": "PruebaSegura456!",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                username="usuario_email_invalido"
            ).exists()
        )

    def test_formulario_no_permite_asignar_grupo_administrador(self):
        from .forms import UsuarioForm

        formulario = UsuarioForm(
            data={
                "username": "nuevo_admin_no_permitido",
                "first_name": "Usuario",
                "last_name": "Prueba",
                "email": "nuevo.admin@example.com",
                "groups": [self.grupo_admin.pk],
                "password1": "PruebaSegura789!",
                "password2": "PruebaSegura789!",
            }
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn("groups", formulario.errors)

    def test_no_crea_usuario_con_correo_duplicado(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("crear_usuario"),
            {
                "username": "usuario_correo_duplicado",
                "first_name": "Juan",
                "last_name": "Perez",
                "email": "ADMIN_TEST@EXAMPLE.COM",
                "groups": [self.grupo_cajero.pk],
                "password1": "PruebaSegura456!",
                "password2": "PruebaSegura456!",
            },
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                username="usuario_correo_duplicado"
            ).exists()
        )

    def test_no_se_puede_desactivar_al_ultimo_administrador(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[self.admin.pk],
            )
        )

        self.admin.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(self.admin.is_active)

    def test_usuario_anonimo_no_pertenece_a_ningun_grupo(self):
        from django.contrib.auth.models import AnonymousUser
        from .templatetags.permisos import tiene_grupo

        usuario = AnonymousUser()

        resultado = tiene_grupo(usuario, "Administrador")

        self.assertFalse(resultado)

    def test_no_permite_contrasena_menor_a_12_caracteres(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("crear_usuario"),
            {
                "username": "usuario_clave_corta",
                "first_name": "Pedro",
                "last_name": "Prueba",
                "email": "pedro.cort@example.com",
                "groups": [self.grupo_cajero.pk],
                "password1": "Clave123!",
                "password2": "Clave123!",
            },
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            User.objects.filter(
                username="usuario_clave_corta"
            ).exists()
        )

        self.assertIn(
            "password2",
            respuesta.context["form"].errors
        )

    def test_puede_desactivar_administrador_si_existe_otro_activo(self):

        segundo_admin = User.objects.create_user(
            username="segundo_admin_test",
            password="PruebaSegura123!",
        )

        segundo_admin.groups.add(self.grupo_admin)

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse(
                "cambiar_estado_usuario",
                args=[segundo_admin.pk],
            )
        )

        segundo_admin.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(segundo_admin.is_active)
        self.assertTrue(User.objects.filter(
            groups__name="Administrador",
            is_active=True,
        ).exists())

class ConcurrenciaAdministradoresTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.grupo_admin, _ = Group.objects.get_or_create(
            name="Administrador"
        )

        self.admin1 = User.objects.create_user(
            username="admin_concurrencia_1",
            password="PruebaSegura123!",
        )
        self.admin1.groups.add(self.grupo_admin)

        self.admin2 = User.objects.create_user(
            username="admin_concurrencia_2",
            password="PruebaSegura123!",
        )
        self.admin2.groups.add(self.grupo_admin)

    def test_dos_administradores_no_pueden_desactivarse_simultaneamente(self):

        if not connection.features.has_select_for_update:
            self.skipTest(
                "Esta prueba requiere una base de datos con bloqueo de filas."
            )

        barrera = threading.Barrier(2)
        resultados = Queue()

        def desactivar_administrador(usuario_id, objetivo_id):

            close_old_connections()

            try:
                usuario = User.objects.get(pk=usuario_id)

                cliente = self.client_class()
                cliente.force_login(usuario)

                barrera.wait(timeout=10)

                respuesta = cliente.post(
                    reverse(
                        "cambiar_estado_usuario",
                        args=[objetivo_id],
                    ),
                    secure=True,
                )

                resultados.put(respuesta.status_code)

            except Exception as error:
                resultados.put(error)

            finally:
                close_old_connections()

        hilo1 = threading.Thread(
            target=desactivar_administrador,
            args=(self.admin1.pk, self.admin2.pk),
        )

        hilo2 = threading.Thread(
            target=desactivar_administrador,
            args=(self.admin2.pk, self.admin1.pk),
        )

        hilo1.start()
        hilo2.start()

        hilo1.join(timeout=30)
        hilo2.join(timeout=30)

        self.assertFalse(hilo1.is_alive(), "El primer hilo quedó bloqueado.")
        self.assertFalse(hilo2.is_alive(), "El segundo hilo quedó bloqueado.")

        resultado1 = resultados.get(timeout=5)
        resultado2 = resultados.get(timeout=5)

        if isinstance(resultado1, Exception):
            raise resultado1

        if isinstance(resultado2, Exception):
            raise resultado2

        self.admin1.refresh_from_db()
        self.admin2.refresh_from_db()

        administradores_activos = User.objects.filter(
            groups__name="Administrador",
            is_active=True,
        ).distinct().count()

        self.assertIn(resultado1, [301, 302])
        self.assertIn(resultado2, [301, 302])
        self.assertEqual(
            administradores_activos,
            1,
            "Debe permanecer exactamente un administrador activo.",
        )
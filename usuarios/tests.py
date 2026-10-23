from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group


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

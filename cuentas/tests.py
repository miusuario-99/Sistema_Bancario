from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User, Group
from clientes.models import Cliente
from movimientos.models import Movimiento
from cuentas.models import Cuenta, CorrelativoCuenta
from .forms import CuentaForm
from auditoria.models import Auditoria
from unittest.mock import patch
import threading
from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

@override_settings(SECURE_SSL_REDIRECT=False)
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

    def test_admin_no_puede_desactivar_cuenta_con_saldo_positivo(self):
        # La cuenta tiene saldo pendiente.
        self.cuenta.saldo = Decimal("1100.00")
        self.cuenta.save(update_fields=["saldo"])

        # Registrar un movimiento de prueba.
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

        # Debe redirigir a la lista de cuentas.
        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()

        # La cuenta debe seguir activa.
        self.assertEqual(self.cuenta.estado, "A")

        # El saldo debe permanecer intacto.
        self.assertEqual(self.cuenta.saldo, Decimal("1100.00"))

        # La cuenta y su historial deben conservarse.
        self.assertTrue(
            Cuenta.objects.filter(id=self.cuenta.id).exists()
        )
        self.assertTrue(
            Movimiento.objects.filter(cuenta=self.cuenta).exists()
        )

    def test_admin_puede_desactivar_cuenta_con_saldo_cero(self):
        self.cuenta.saldo = Decimal("0.00")
        self.cuenta.save(update_fields=["saldo"])

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("eliminar_cuenta", args=[self.cuenta.id])
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()

        # La cuenta se conserva, pero queda inactiva.
        self.assertTrue(
            Cuenta.objects.filter(id=self.cuenta.id).exists()
        )
        self.assertEqual(self.cuenta.estado, "I")
        self.assertEqual(self.cuenta.saldo, Decimal("0.00"))

    def test_admin_no_puede_reactivar_cuenta_inactiva_desde_edicion(self):
        self.cuenta.saldo = Decimal("0.00")
        self.cuenta.estado = "I"
        self.cuenta.save(update_fields=["saldo", "estado"])

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("editar_cuenta", args=[self.cuenta.id]),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "cliente": self.cliente.id,
                "tipo_cuenta": self.cuenta.tipo_cuenta,
                "saldo": "0.00",
                "estado": "A",
            },
        )

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.estado, "I")

    def test_supervisor_no_puede_crear_cuenta(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.post(
            reverse("nueva_cuenta"),
            {
                "cliente": self.cliente.id,
                "tipo_cuenta": "AH",
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.assertEqual(Cuenta.objects.count(), 1)

    def test_cajero_no_puede_crear_cuenta(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            reverse("nueva_cuenta"),
            {
                "cliente": self.cliente.id,
                "tipo_cuenta": "AH",
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.assertEqual(Cuenta.objects.count(), 1)

    def test_supervisor_no_puede_editar_cuenta(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.post(
            reverse("editar_cuenta", args=[self.cuenta.id]),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "cliente": self.cliente.id,
                "tipo_cuenta": "CC",
                "saldo": "1000.00",
                "estado": "A",
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.tipo_cuenta, "AH")

    def test_cajero_no_puede_editar_cuenta(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            reverse("editar_cuenta", args=[self.cuenta.id]),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "cliente": self.cliente.id,
                "tipo_cuenta": "CC",
                "saldo": "1000.00",
                "estado": "A",
            },
        )

        self.assertEqual(respuesta.status_code, 403)

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.tipo_cuenta, "AH")

    def test_supervisor_no_puede_desactivar_cuenta(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.post(
            reverse("eliminar_cuenta", args=[self.cuenta.id])
        )

        self.assertEqual(respuesta.status_code, 403)

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.estado, "A")
        self.assertEqual(self.cuenta.saldo, Decimal("1000.00"))

    def test_cajero_no_puede_desactivar_cuenta(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.post(
            reverse("eliminar_cuenta", args=[self.cuenta.id])
        )

        self.assertEqual(respuesta.status_code, 403)

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.estado, "A")
        self.assertEqual(self.cuenta.saldo, Decimal("1000.00"))

    def test_cajero_no_puede_exportar_cuentas_excel(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("cuentas_excel")
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_exportar_cuentas_pdf(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("cuentas_pdf")
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_supervisor_puede_exportar_cuentas_excel(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.get(
            reverse("cuentas_excel")
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_supervisor_puede_exportar_cuentas_pdf(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.get(
            reverse("cuentas_pdf")
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf"
        )
    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_admin_crea_cuenta_con_siguiente_correlativo(self):

        CorrelativoCuenta.objects.create(
            clave="cuenta",
            ultimo_numero=2
        )

        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("nueva_cuenta"),
            {
                "cliente": self.cliente.id,
                "tipo_cuenta": "AH",
            }
        )

        print("URL:", respuesta.url if hasattr(respuesta, "url") else respuesta.headers.get("Location"))

        self.assertEqual(respuesta.status_code, 302)

        cuenta_nueva = Cuenta.objects.get(
            numero_cuenta="CTA-000003"
        )

        self.assertEqual(cuenta_nueva.saldo, Decimal("0.00"))

        contador = CorrelativoCuenta.objects.get(clave="cuenta")

        self.assertEqual(contador.ultimo_numero, 3)

        self.assertTrue(
            Auditoria.objects.filter(
                accion="Nueva cuenta",
                descripcion__contains="CTA-000003"
            ).exists()
        )

    @patch(
        "cuentas.views.registrar_auditoria",
        side_effect=Exception("Error simulado de auditoría")
    )

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_error_auditoria_revierte_creacion_de_cuenta(
        self, mock_auditoria
    ):

        CorrelativoCuenta.objects.create(
            clave="cuenta",
            ultimo_numero=2
        )

        self.client.force_login(self.admin)

        with self.assertRaises(Exception):
            self.client.post(
                reverse("nueva_cuenta"),
                {
                    "cliente": self.cliente.id,
                    "tipo_cuenta": "AH",
                }
            )

        # No debe haberse creado la cuenta.
        self.assertFalse(
            Cuenta.objects.filter(numero_cuenta="CTA-000003").exists()
        )

        # El contador debe conservar su valor anterior.
        contador = CorrelativoCuenta.objects.get(clave="cuenta")
        self.assertEqual(contador.ultimo_numero, 2)

        # No debe existir una auditoría de creación.
        self.assertFalse(
            Auditoria.objects.filter(
                accion="Nueva cuenta"
            ).exists()
        )

class CuentaFormClienteEstadoTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cliente_activo = Cliente.objects.create(
            dni="11111111",
            nombres="Cliente",
            apellidos="Activo Prueba",
            fecha_nacimiento="1990-01-15",
            direccion="Lima",
            telefono="999111111",
            correo="activo_prueba@example.com",
            estado="A",
        )

        cls.cliente_inactivo = Cliente.objects.create(
            dni="22222222",
            nombres="Cliente",
            apellidos="Inactivo Prueba",
            fecha_nacimiento="1990-01-15",
            direccion="Lima",
            telefono="999222222",
            correo="inactivo_prueba@example.com",
            estado="I",
        )

    def datos_cuenta(self, cliente):
        return {
            "numero_cuenta": "CTA-900001",
            "cliente": cliente.pk,
            "tipo_cuenta": "AH",
            "saldo": "100.00",
            "estado": "A",
        }

    def test_cuenta_nueva_acepta_cliente_activo(self):
        form = CuentaForm(
            data=self.datos_cuenta(self.cliente_activo)
        )

        self.assertTrue(
            form.is_valid(),
            msg=str(form.errors),
        )

    def test_cuenta_nueva_rechaza_cliente_inactivo(self):
        form = CuentaForm(
            data=self.datos_cuenta(self.cliente_inactivo)
        )

        self.assertFalse(form.is_valid())

        self.assertIn("cliente", form.errors)

    def test_editar_cuenta_conserva_cliente_actual_inactivo(self):
        self.cliente_activo.estado = "I"
        self.cliente_activo.save(update_fields=["estado"])

        cuenta = Cuenta.objects.create(
            numero_cuenta="CTA-900002",
            cliente=self.cliente_activo,
            tipo_cuenta="AH",
            saldo=Decimal("100.00"),
            estado="A",
        )

        datos = self.datos_cuenta(self.cliente_activo)
        datos["numero_cuenta"] = cuenta.numero_cuenta

        form = CuentaForm(
            data=datos,
            instance=cuenta,
        )

        self.assertTrue(
            form.is_valid(),
            msg=str(form.errors),
        )

    def test_editar_cuenta_rechaza_cambiar_a_otro_cliente_inactivo(self):
        cuenta = Cuenta.objects.create(
            numero_cuenta="CTA-900003",
            cliente=self.cliente_activo,
            tipo_cuenta="AH",
            saldo=Decimal("100.00"),
            estado="A",
        )

        datos = self.datos_cuenta(self.cliente_inactivo)
        datos["numero_cuenta"] = cuenta.numero_cuenta

        form = CuentaForm(
            data=datos,
            instance=cuenta,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cliente", form.errors)

@skipUnlessDBFeature("has_select_for_update")
class CreacionCuentasConcurrentesTests(TransactionTestCase):
    def setUp(self):

        self.grupo_admin = Group.objects.create(
            name="Administrador"
        )

        self.admin1 = User.objects.create_user(
            username="admin_concurrente1",
            password="PruebaSegura2026!"
        )
        self.admin1.groups.add(self.grupo_admin)

        self.admin2 = User.objects.create_user(
            username="admin_concurrente2",
            password="PruebaSegura2026!"
        )
        self.admin2.groups.add(self.grupo_admin)

        self.cliente = Cliente.objects.create(
            dni="88888888",
            nombres="Cliente",
            apellidos="Prueba Cuentas Concurrentes",
            fecha_nacimiento="1990-01-01",
            direccion="Lima",
            telefono="999999999",
            correo="cuentas_concurrentes@example.com",
            estado="A",
        )

        CorrelativoCuenta.objects.create(
            clave="cuenta",
            ultimo_numero=0
        )

        self.url = reverse("nueva_cuenta")

    def test_dos_administradores_crean_cuentas_simultaneamente(self):
        barrera = threading.Barrier(2)
        resultados = []
        errores = []
        bloqueo_resultados = threading.Lock()

        def crear_cuenta(admin):

            close_old_connections()

            try:
                cliente_http = self.client_class()
                cliente_http.force_login(admin)

                barrera.wait(timeout=10)

                respuesta = cliente_http.post(
                    self.url,
                    {
                        "cliente": self.cliente.id,
                        "tipo_cuenta": "AH",
                    },
                    secure=True,
                    follow=True,
                )

                with bloqueo_resultados:
                    resultados.append({
                        "admin": admin.username,
                        "status": respuesta.status_code,
                    })

            except Exception as error:
                with bloqueo_resultados:
                    errores.append(repr(error))

            finally:
                close_old_connections()

                hilos = [
                    threading.Thread(
                        target=crear_cuenta,
                        args=(self.admin1,),
                    ),
                    threading.Thread(
                        target=crear_cuenta,
                        args=(self.admin2,),
                    ),
                ]


                for hilo in hilos:
                    hilo.start()

                for hilo in hilos:
                    hilo.join(timeout=30)

                self.assertFalse(
                    any(hilo.is_alive() for hilo in hilos),
                    "Una creación de cuenta quedó bloqueada más de 30 segundos."
                )

                self.assertEqual(
                    errores,
                    [],
                    f"Errores durante la creación: {errores}"
                )

                self.assertEqual(
                    len(resultados),
                    2,
                    f"Se esperaban dos resultados: {resultados}"
                )

                cuentas_creadas = Cuenta.objects.filter(
                    numero_cuenta__startswith="CTA-"
                ).order_by("numero_cuenta")

                self.assertEqual(
                    cuentas_creadas.count(),
                    2,
                    "Deben crearse exactamente dos cuentas."
                )

                numeros = list(
                    cuentas_creadas.values_list(
                        "numero_cuenta",
                        flat=True
                    )
                )

                self.assertEqual(
                    numeros,
                    ["CTA-000001", "CTA-000002"]
                )

                cuentas_creadas = Cuenta.objects.filter(
                    numero_cuenta__startswith="CTA-"
                ).order_by("numero_cuenta")

                self.assertEqual(
                    cuentas_creadas.count(),
                    2,
                    "Deben crearse exactamente dos cuentas."
                )

                numeros = list(
                    cuentas_creadas.values_list(
                        "numero_cuenta",
                        flat=True
                    )
                )

                self.assertEqual(
                    numeros,
                    ["CTA-000001", "CTA-000002"]
                )

                contador = CorrelativoCuenta.objects.get(clave="cuenta")

                self.assertEqual(
                    contador.ultimo_numero,
                    2,
                    "El correlativo debe terminar en 2."
                )
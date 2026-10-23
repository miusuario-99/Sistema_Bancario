from decimal import Decimal
from auditoria.models import Auditoria
from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.urls import reverse
from clientes.models import Cliente
from cuentas.models import Cuenta
from movimientos.models import Movimiento
import threading
from django.db import close_old_connections
from django.test import TransactionTestCase
from unittest.mock import patch


class SeguridadTransferenciaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear grupos
        cls.grupo_cajero = Group.objects.create(name="Cajero")
        cls.grupo_supervisor = Group.objects.create(name="Supervisor")

        # Crear usuarios de prueba
        cls.cajero = User.objects.create_user(
            username="cajero_prueba",
            password="PruebaSegura2026!"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.supervisor = User.objects.create_user(
            username="supervisor_prueba",
            password="PruebaSegura2026!"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        # Crear cliente con todos los campos obligatorios
        cls.cliente = Cliente.objects.create(
            dni="99999999",
            nombres="Cliente",
            apellidos="Prueba",
            fecha_nacimiento="1990-01-15",
            direccion="Dirección de prueba",
            telefono="999999999",
            correo="prueba@example.com",
            estado="A"
        )

        # Crear cuentas para probar transferencias
        cls.origen = Cuenta.objects.create(
            numero_cuenta="TEST000001",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("1000.00"),
            estado="A"
        )

        cls.destino = Cuenta.objects.create(
            numero_cuenta="TEST000002",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("500.00"),
            estado="A"
        )

    def setUp(self):
        self.client.force_login(self.cajero)
        self.url = reverse("transferencia")

    def enviar_transferencia(self, monto):
        return self.client.post(
            self.url,
            {
                "origen": self.origen.numero_cuenta,
                "destino": self.destino.numero_cuenta,
                "monto": monto,
            }
        )

    def comprobar_rechazo_sin_cambios(self, monto):
        respuesta = self.enviar_transferencia(monto)

        self.assertEqual(respuesta.status_code, 302)

        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_rechaza_monto_cero(self):
        self.comprobar_rechazo_sin_cambios("0")

    def test_rechaza_monto_negativo(self):
        self.comprobar_rechazo_sin_cambios("-10")

    def test_rechaza_mas_de_dos_decimales(self):
        self.comprobar_rechazo_sin_cambios("10.123")

    def test_supervisor_no_puede_transferir(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.post(
            self.url,
            {
                "origen": self.origen.numero_cuenta,
                "destino": self.destino.numero_cuenta,
                "monto": "10.00",
            }
        )

        self.assertEqual(respuesta.status_code, 403)

        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_rechaza_transferencia_a_la_misma_cuenta(self):
        respuesta = self.client.post(
            self.url,
            {
                "origen": self.origen.numero_cuenta,
                "destino": self.origen.numero_cuenta,
                "monto": "100.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_rechaza_saldo_insuficiente(self):
        respuesta = self.enviar_transferencia("1500.00")

        self.assertEqual(respuesta.status_code, 302)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_rechaza_cuenta_origen_inactiva(self):
        self.origen.estado = "I"
        self.origen.save(update_fields=["estado"])

        respuesta = self.enviar_transferencia("100.00")

        self.assertEqual(respuesta.status_code, 302)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_rechaza_cuenta_destino_inactiva(self):
        self.destino.estado = "I"
        self.destino.save(update_fields=["estado"])

        respuesta = self.enviar_transferencia("100.00")

        self.assertEqual(respuesta.status_code, 302)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("1000.00"))
        self.assertEqual(self.destino.saldo, Decimal("500.00"))
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_transferencia_valida_actualiza_saldos_y_movimientos(self):
        respuesta = self.enviar_transferencia("100.00")

        self.assertEqual(respuesta.status_code, 302)
        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(self.origen.saldo, Decimal("900.00"))
        self.assertEqual(self.destino.saldo, Decimal("600.00"))
        self.assertEqual(Movimiento.objects.count(), 2)

        movimientos = Movimiento.objects.filter(tipo="T").order_by("id")
        self.assertEqual(movimientos.count(), 2)

        self.assertEqual(
            movimientos.filter(
                cuenta=self.origen,
                monto=Decimal("100.00")
            ).count(),
            1
        )

        self.assertEqual(
            movimientos.filter(
                cuenta=self.destino,
                monto=Decimal("100.00")
            ).count(),
            1
        )

        # Verificar el registro de auditoría
        registro = Auditoria.objects.filter(
            usuario=self.cajero,
            modulo="Movimientos",
            accion="Transferencia",
        ).first()

        self.assertIsNotNone(registro)

        self.assertIn(
            self.origen.numero_cuenta,
            registro.descripcion
        )

        self.assertIn(
            self.destino.numero_cuenta,
            registro.descripcion
        )

    @patch(
        "movimientos.views.registrar_auditoria",
        side_effect=RuntimeError("Error de auditoría simulado")
    )
    def test_transferencia_se_revierte_si_falla_auditoria(
        self,
        mock_auditoria
    ):
        with self.assertRaises(RuntimeError):
            self.enviar_transferencia("100.00")

        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        # Los saldos deben conservar sus valores originales.
        self.assertEqual(
            self.origen.saldo,
            Decimal("1000.00")
        )
        self.assertEqual(
            self.destino.saldo,
            Decimal("500.00")
        )

        # Ninguno de los dos movimientos debe quedar guardado.
        self.assertEqual(Movimiento.objects.count(), 0)

        # La auditoría debe haberse intentado registrar.
        mock_auditoria.assert_called_once()

    def test_transferencia_que_supera_saldo_maximo_es_rechazada(self):
        self.destino.saldo = Decimal("9999999999.50")
        self.destino.save(update_fields=["saldo"])

        respuesta = self.enviar_transferencia("0.51")

        self.assertEqual(respuesta.status_code, 302)

        self.origen.refresh_from_db()
        self.destino.refresh_from_db()

        self.assertEqual(
            self.origen.saldo,
            Decimal("1000.00")
        )
        self.assertEqual(
            self.destino.saldo,
            Decimal("9999999999.50")
        )

        self.assertEqual(Movimiento.objects.count(), 0)

        self.assertEqual(
            Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Transferencia",
            ).count(),
            0
        )

class SeguridadDepositoRetiroTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.grupo_cajero = Group.objects.create(name="Cajero")

        cls.cajero = User.objects.create_user(
            username="cajero_deposito_prueba",
            password="PruebaSegura2026!"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.cliente = Cliente.objects.create(
            dni="88888888",
            nombres="Cliente",
            apellidos="Deposito Retiro",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="988888888",
            correo="deposito@example.com",
            estado="A"
        )

        cls.cuenta = Cuenta.objects.create(
            numero_cuenta="TEST000003",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("1000.00"),
            estado="A"
        )

    def setUp(self):
        self.client.force_login(self.cajero)

    def comprobar_saldo_y_movimientos_sin_cambios(self):
        self.cuenta.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("1000.00")
        )
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_deposito_valido_actualiza_saldo(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "200.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.saldo, Decimal("1200.00"))

        movimiento = Movimiento.objects.get()
        self.assertEqual(movimiento.tipo, "D")
        self.assertEqual(movimiento.monto, Decimal("200.00"))

        registro = Auditoria.objects.get(
            usuario=self.cajero,
            modulo="Movimientos",
            accion="Depósito",
        )

        self.assertIn(
            self.cuenta.numero_cuenta,
            registro.descripcion
        )
        self.assertIn("200.00", registro.descripcion)

    def test_deposito_que_supera_saldo_maximo_es_rechazado(self):
        self.cuenta.saldo = Decimal("9999999999.00")
        self.cuenta.save(update_fields=["saldo"])

        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "1.01",
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("9999999999.00")
        )

        self.assertEqual(Movimiento.objects.count(), 0)

        self.assertEqual(
            Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Depósito",
            ).count(),
            0
        )

    def test_deposito_cero_es_rechazado(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "0",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_deposito_negativo_es_rechazado(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "-10",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_deposito_con_mas_de_dos_decimales_es_rechazado(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "10.123",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_deposito_en_cuenta_inactiva_es_rechazado(self):
        self.cuenta.estado = "I"
        self.cuenta.save(update_fields=["estado"])

        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "100.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_retiro_valido_actualiza_saldo(self):
        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "200.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()
        self.assertEqual(self.cuenta.saldo, Decimal("800.00"))

        movimiento = Movimiento.objects.get()
        self.assertEqual(movimiento.tipo, "R")
        self.assertEqual(movimiento.monto, Decimal("200.00"))

        registro = Auditoria.objects.get(
            usuario=self.cajero,
            modulo="Movimientos",
            accion="Retiro",
        )

        self.assertIn(
            self.cuenta.numero_cuenta,
            registro.descripcion
        )
        self.assertIn("200.00", registro.descripcion)

    def test_retiro_superior_al_saldo_es_rechazado(self):
        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "1500.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_retiro_cero_es_rechazado(self):
        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "0",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_retiro_en_cuenta_inactiva_es_rechazado(self):
        self.cuenta.estado = "I"
        self.cuenta.save(update_fields=["estado"])

        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "100.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

    @patch(
        "movimientos.views.registrar_auditoria",
        side_effect=RuntimeError("Error de auditoría simulado")
    )
    def test_deposito_se_revierte_si_falla_auditoria(
        self,
        mock_auditoria
    ):
        saldo_original = self.cuenta.saldo

        with self.assertRaises(RuntimeError):
            self.client.post(
                reverse("deposito"),
                {
                    "numero_cuenta": self.cuenta.numero_cuenta,
                    "monto": "100.00",
                }
            )

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.saldo, saldo_original)
        self.assertEqual(Movimiento.objects.count(), 0)

        mock_auditoria.assert_called_once()

    @patch(
        "movimientos.views.registrar_auditoria",
        side_effect=RuntimeError("Error de auditoría simulado")
    )
    def test_retiro_se_revierte_si_falla_auditoria(
        self,
        mock_auditoria
    ):
        saldo_original = self.cuenta.saldo

        with self.assertRaises(RuntimeError):
            self.client.post(
                reverse("retiro"),
                {
                    "numero_cuenta": self.cuenta.numero_cuenta,
                    "monto": "100.00",
                }
            )

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.saldo, saldo_original)
        self.assertEqual(Movimiento.objects.count(), 0)

        mock_auditoria.assert_called_once()

class SeguridadReportesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.grupo_cajero, _ = Group.objects.get_or_create(
            name="Cajero"
        )
        cls.grupo_supervisor, _ = Group.objects.get_or_create(
            name="Supervisor"
        )

        cls.cajero = User.objects.create_user(
            username="cajero_reportes_prueba",
            password="PruebaSegura123"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.supervisor = User.objects.create_user(
            username="supervisor_reportes_prueba",
            password="PruebaSegura123"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

    def test_cajero_no_puede_ver_pdf(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("reporte_movimientos_pdf")
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_cajero_no_puede_ver_excel(self):
        self.client.force_login(self.cajero)

        respuesta = self.client.get(
            reverse("reporte_movimientos_excel")
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_supervisor_puede_acceder_pdf(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.get(
            reverse("reporte_movimientos_pdf")
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_supervisor_puede_acceder_excel(self):
        self.client.force_login(self.supervisor)

        respuesta = self.client.get(
            reverse("reporte_movimientos_excel")
        )

        self.assertEqual(respuesta.status_code, 200)

    def test_usuario_sin_sesion_no_accede_pdf(self):
        respuesta = self.client.get(
            reverse("reporte_movimientos_pdf")
        )

        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_accede_excel(self):
        respuesta = self.client.get(
            reverse("reporte_movimientos_excel")
        )

        self.assertEqual(respuesta.status_code, 302)

class TransferenciasConcurrentesTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.grupo_cajero = Group.objects.create(name="Cajero")

        self.cajero = User.objects.create_user(
            username="cajero_concurrencia",
            password="PruebaSegura2026!"
        )
        self.cajero.groups.add(self.grupo_cajero)

        self.cliente = Cliente.objects.create(
            dni="88888888",
            nombres="Cliente",
            apellidos="Prueba Concurrencia",
            fecha_nacimiento="1990-01-01",
            direccion="Lima",
            telefono="999999999",
            correo="concurrencia@example.com",
            estado="A",
        )

        self.origen = Cuenta.objects.create(
            numero_cuenta="CONC000001",
            cliente=self.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("100.00"),
            estado="A",
        )

        self.destino1 = Cuenta.objects.create(
            numero_cuenta="CONC000002",
            cliente=self.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("0.00"),
            estado="A",
        )

        self.destino2 = Cuenta.objects.create(
            numero_cuenta="CONC000003",
            cliente=self.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("0.00"),
            estado="A",
        )

        self.url = reverse("transferencia")

    def test_dos_transferencias_simultaneas_no_generan_saldo_negativo(self):
            barrera = threading.Barrier(2)
            resultados = []
            errores = []
            bloqueo_resultados = threading.Lock()

            def ejecutar_transferencia(numero_destino):
                close_old_connections()

                try:
                    cliente_http = self.client_class()

                    usuario = User.objects.get(pk=self.cajero.pk)
                    cliente_http.force_login(usuario)

                    # Ambas solicitudes esperan antes de comenzar.
                    barrera.wait(timeout=10)

                    respuesta = cliente_http.post(
                        self.url,
                        {
                            "origen": self.origen.numero_cuenta,
                            "destino": numero_destino,
                            "monto": "80.00",
                        },
                        follow=True,
                    )

                    # Recoger los mensajes de Django sin depender del
                    # contexto de plantilla de la respuesta.
                    mensajes = []
                    for mensaje in list(respuesta.wsgi_request._messages):
                        mensajes.append(str(mensaje))

                    with bloqueo_resultados:
                        resultados.append({
                            "destino": numero_destino,
                            "status": respuesta.status_code,
                            "mensajes": mensajes,
                        })

                except Exception as error:
                    with bloqueo_resultados:
                        errores.append(repr(error))

                finally:
                    close_old_connections()

            hilos = [
                threading.Thread(
                    target=ejecutar_transferencia,
                    args=(self.destino1.numero_cuenta,),
                ),
                threading.Thread(
                    target=ejecutar_transferencia,
                    args=(self.destino2.numero_cuenta,),
                ),
            ]

            for hilo in hilos:
                hilo.start()

            for hilo in hilos:
                hilo.join(timeout=30)

            self.assertFalse(
                any(hilo.is_alive() for hilo in hilos),
                "Una transferencia quedó bloqueada más de 30 segundos.",
            )

            self.assertEqual(
                errores,
                [],
                f"Errores durante las transferencias: {errores}",
            )

            self.assertEqual(
                len(resultados),
                2,
                f"Se esperaban dos resultados: {resultados}",
            )

            # Comprobar saldos definitivos.
            self.origen.refresh_from_db()
            self.destino1.refresh_from_db()
            self.destino2.refresh_from_db()

            self.assertEqual(self.origen.saldo, Decimal("20.00"))

            self.assertEqual(
                self.destino1.saldo + self.destino2.saldo,
                Decimal("80.00"),
            )

            self.assertGreaterEqual(self.origen.saldo, Decimal("0.00"))

            # Debe existir exactamente una transferencia completada:
            # cada transferencia crea dos movimientos.
            movimientos = Movimiento.objects.filter(
                cuenta__numero_cuenta__in=[
                    self.origen.numero_cuenta,
                    self.destino1.numero_cuenta,
                    self.destino2.numero_cuenta,
                ]
            )

            self.assertEqual(movimientos.count(), 2)

            # El destino que recibió los fondos debe tener S/ 80;
            # el otro debe conservar S/ 0.
            saldos_destinos = sorted([
                self.destino1.saldo,
                self.destino2.saldo,
            ])

            self.assertEqual(
                saldos_destinos,
                [Decimal("0.00"), Decimal("80.00")],
            )

            # Mostrar resultados para el diagnóstico.
            print("\nResultados de transferencias concurrentes:")
            for resultado in resultados:
                print(resultado)

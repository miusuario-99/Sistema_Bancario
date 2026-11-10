from decimal import Decimal
from auditoria.models import Auditoria
from django.contrib.auth.models import User, Group
from django.urls import reverse
from clientes.models import Cliente
from cuentas.models import Cuenta
from movimientos.models import Movimiento, OperacionBancaria
import threading
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from unittest.mock import patch
from django.db.models.deletion import ProtectedError
import uuid
from django.db import connection
from django.db import close_old_connections

class SeguridadTransferenciaTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear grupos
        cls.grupo_cajero = Group.objects.create(name="Cajero")
        cls.grupo_supervisor = Group.objects.create(name="Supervisor")
        cls.grupo_admin = Group.objects.create(name="Administrador")

        # Crear usuarios de prueba
        cls.cajero = User.objects.create_user(
            username="cajero_prueba",
            password="PruebaSegura2026!"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.admin = User.objects.create_user(
            username="admin_transferencia_prueba",
            password="PruebaSegura2026!"
        )
        cls.admin.groups.add(cls.grupo_admin)


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
        self.client.force_login(self.admin)
        self.url = reverse("transferencia")

    def enviar_transferencia(self, monto):
        return self.client.post(
            self.url,
            {
                "origen": self.origen.numero_cuenta,
                "destino": self.destino.numero_cuenta,
                "monto": monto,
                "idempotency_key": str(uuid.uuid4()),
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

    def comprobar_acceso_denegado(self, usuario, nombre_url):
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse(nombre_url))
        self.assertEqual(respuesta.status_code, 403)

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
            usuario=self.admin,
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

        # No debe quedar ningún registro de auditoría.
        self.assertEqual(
            Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Transferencia",
            ).count(),
            0
        )

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
        cls.grupo_admin = Group.objects.create(name="Administrador")

        cls.cajero = User.objects.create_user(
            username="cajero_deposito_prueba",
            password="PruebaSegura2026!"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.admin = User.objects.create_user(
            username="admin_deposito_prueba",
            password="PruebaSegura2026!"
        )
        cls.admin.groups.add(cls.grupo_admin)

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

        cls.cuenta_destino = Cuenta.objects.create(
            numero_cuenta="TEST000004",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("500.00"),
            estado="A"
        )

    def setUp(self):
        self.client.force_login(self.cajero)

    def obtener_idempotency_key(self):
        return str(uuid.uuid4())

    def enviar_transferencia_como_admin(self, datos):
        self.client.force_login(self.admin)
        return self.client.post(reverse("transferencia"), datos)

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
                "idempotency_key": self.obtener_idempotency_key(),
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

    def test_deposito_en_cuenta_inactiva_es_rechazado(self):
        # Desactivar la cuenta
        self.cuenta.estado = "I"
        self.cuenta.save(update_fields=["estado"])

        # Intentar depositar en la cuenta inactiva
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "200.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        # Comprobar que el saldo y los movimientos no cambiaron
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_retiro_de_cuenta_inactiva_es_rechazado(self):
        # Desactivar la cuenta
        self.cuenta.estado = "I"
        self.cuenta.save(update_fields=["estado"])

        # Intentar retirar dinero de la cuenta inactiva
        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "200.00",
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        # Comprobar que el saldo y los movimientos no cambiaron
        self.comprobar_saldo_y_movimientos_sin_cambios()

    def test_deposito_negativo_es_rechazado(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "-10",
                "idempotency_key": self.obtener_idempotency_key(),
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()


    def test_deposito_duplicado_no_modifica_dos_veces_el_saldo(self):

        idempotency_key = str(uuid.uuid4())

        datos = {
            "numero_cuenta": self.cuenta.numero_cuenta,
            "monto": "200.00",
            "idempotency_key": idempotency_key,
        }

        respuesta1 = self.client.post(
            reverse("deposito"),
            datos
        )

        respuesta2 = self.client.post(
            reverse("deposito"),
            datos
        )

        self.assertEqual(respuesta1.status_code, 302)
        self.assertEqual(respuesta2.status_code, 302)

        self.cuenta.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("1200.00")
        )

        self.assertEqual(
            OperacionBancaria.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1
        )

        self.assertEqual(Movimiento.objects.count(), 1)

    def test_retiro_duplicado_no_modifica_dos_veces_el_saldo(self):

        idempotency_key = str(uuid.uuid4())

        datos = {
            "numero_cuenta": self.cuenta.numero_cuenta,
            "monto": "200.00",
            "idempotency_key": idempotency_key,
        }

        respuesta1 = self.client.post(
            reverse("retiro"),
            datos
        )

        respuesta2 = self.client.post(
            reverse("retiro"),
            datos
        )

        self.assertEqual(respuesta1.status_code, 302)
        self.assertEqual(respuesta2.status_code, 302)

        self.cuenta.refresh_from_db()

        # El saldo solo debe disminuir una vez.
        self.assertEqual(
            self.cuenta.saldo,
            Decimal("800.00")
        )

        self.assertEqual(
            OperacionBancaria.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1
        )

        self.assertEqual(Movimiento.objects.count(), 1)

    def test_transferencia_duplicada_no_modifica_dos_veces_los_saldos(self):

        idempotency_key = str(uuid.uuid4())

        datos = {
            "origen": self.cuenta.numero_cuenta,
            "destino": self.cuenta_destino.numero_cuenta,
            "monto": "200.00",
            "idempotency_key": idempotency_key,
        }

        respuesta = self.enviar_transferencia_como_admin(datos)

        respuesta2 = self.enviar_transferencia_como_admin(datos)

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta2.status_code, 302)

        self.cuenta.refresh_from_db()
        self.cuenta_destino.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("800.00")
        )

        self.assertEqual(
            self.cuenta_destino.saldo,
            Decimal("700.00")
        )

        self.assertEqual(
            OperacionBancaria.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1
        )

        movimientos = Movimiento.objects.filter(
            operacion__idempotency_key=idempotency_key
        )

        self.assertEqual(movimientos.count(), 2)

    def test_deposito_con_mas_de_dos_decimales_es_rechazado(self):
        respuesta = self.client.post(
            reverse("deposito"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "10.123",
                "idempotency_key": self.obtener_idempotency_key(),
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
                    "monto": "200.00",
                    "idempotency_key": self.obtener_idempotency_key(),
                }
            )

        self.cuenta.refresh_from_db()

        # El saldo debe conservar su valor original.
        self.assertEqual(
            self.cuenta.saldo,
            saldo_original
        )

        # No debe quedar registrado ningún movimiento.
        self.assertEqual(
            Movimiento.objects.count(),
            0
        )

        # Debe haberse intentado registrar la auditoría.
        mock_auditoria.assert_called_once()

        # No debe quedar ningún registro de auditoría.
        self.assertEqual(
            Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Depósito",
            ).count(),
            0
        )

    def test_retiro_valido_actualiza_saldo(self):
        respuesta = self.client.post(
            reverse("retiro"),
            {
                "numero_cuenta": self.cuenta.numero_cuenta,
                "monto": "200.00",
                "idempotency_key": self.obtener_idempotency_key(),
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
                "idempotency_key": self.obtener_idempotency_key(),
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
                "idempotency_key": self.obtener_idempotency_key(),
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
                "idempotency_key": self.obtener_idempotency_key(),
            }
        )

        self.assertEqual(respuesta.status_code, 302)
        self.comprobar_saldo_y_movimientos_sin_cambios()

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
                    "idempotency_key": self.obtener_idempotency_key(),
                }
            )

        self.cuenta.refresh_from_db()

        self.assertEqual(self.cuenta.saldo, saldo_original)
        self.assertEqual(Movimiento.objects.count(), 0)

        mock_auditoria.assert_called_once()

        # No debe quedar ningún registro de auditoría.
        self.assertEqual(
            Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Retiro",
            ).count(),
            0
        )

    def test_transferencia_valida_actualiza_ambos_saldos(self):
        respuesta = self.enviar_transferencia_como_admin(
            {
                "origen": self.cuenta.numero_cuenta,
                "destino": self.cuenta_destino.numero_cuenta,
                "monto": "200.00",
                "idempotency_key": self.obtener_idempotency_key(),
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()
        self.cuenta_destino.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("800.00")
        )

        self.assertEqual(
            self.cuenta_destino.saldo,
            Decimal("700.00")
        )

        self.assertEqual(Movimiento.objects.count(), 2)

        self.assertTrue(
            Auditoria.objects.filter(
                usuario=self.admin,
                modulo="Movimientos",
                accion="Transferencia",
            ).exists()
        )

    def test_transferencia_con_saldo_insuficiente_es_rechazada(self):
        respuesta = self.enviar_transferencia_como_admin(

            {
                "origen": self.cuenta.numero_cuenta,
                "destino": self.cuenta_destino.numero_cuenta,
                "monto": "1500.00",
                "idempotency_key": self.obtener_idempotency_key(),
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()
        self.cuenta_destino.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("1000.00")
        )

        self.assertEqual(
            self.cuenta_destino.saldo,
            Decimal("500.00")
        )

        self.assertEqual(Movimiento.objects.count(), 0)

    def test_transferencia_a_la_misma_cuenta_es_rechazada(self):
        respuesta = self.enviar_transferencia_como_admin(

            {
                "origen": self.cuenta.numero_cuenta,
                "destino": self.cuenta.numero_cuenta,
                "monto": "100.00",
                "idempotency_key": self.obtener_idempotency_key(),
            }
        )

        self.assertEqual(respuesta.status_code, 302)

        self.cuenta.refresh_from_db()

        self.assertEqual(
            self.cuenta.saldo,
            Decimal("1000.00")
        )

        self.assertEqual(Movimiento.objects.count(), 0)




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

class SeguridadOperacionesBancariasTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear grupos
        cls.grupo_administrador, _ = Group.objects.get_or_create(
            name="Administrador"
        )
        cls.grupo_cajero, _ = Group.objects.get_or_create(
            name="Cajero"
        )
        cls.grupo_supervisor, _ = Group.objects.get_or_create(
            name="Supervisor"
        )

        # Crear usuarios
        cls.administrador = User.objects.create_user(
            username="admin_seguridad_bancaria",
            password="PruebaSegura2026!"
        )
        cls.administrador.groups.add(cls.grupo_administrador)

        cls.cajero = User.objects.create_user(
            username="cajero_seguridad_bancaria",
            password="PruebaSegura2026!"
        )
        cls.cajero.groups.add(cls.grupo_cajero)

        cls.supervisor = User.objects.create_user(
            username="supervisor_seguridad_bancaria",
            password="PruebaSegura2026!"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        cls.usuario_sin_grupo = User.objects.create_user(
            username="usuario_sin_grupo_bancario",
            password="PruebaSegura2026!"
        )

    def comprobar_acceso_denegado(self, usuario, nombre_url):
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse(nombre_url))

        self.assertEqual(respuesta.status_code, 403)

        self.client.logout()

    def comprobar_acceso_permitido(self, usuario, nombre_url):
        self.client.force_login(usuario)

        respuesta = self.client.get(reverse(nombre_url))

        self.assertEqual(respuesta.status_code, 200)

        self.client.logout()

    # El Administrador puede acceder a las operaciones bancarias.

    def test_administrador_puede_acceder_a_deposito(self):
        self.comprobar_acceso_permitido(
            self.administrador,
            "deposito"
        )

    def test_administrador_puede_acceder_a_retiro(self):
        self.comprobar_acceso_permitido(
            self.administrador,
            "retiro"
        )

    def test_administrador_puede_acceder_a_transferencia(self):
        self.comprobar_acceso_permitido(
            self.administrador,
            "transferencia"
        )

    # El Cajero puede acceder a las operaciones bancarias.

    def test_cajero_puede_acceder_a_deposito(self):
        self.comprobar_acceso_permitido(
            self.cajero,
            "deposito"
        )

    def test_cajero_puede_acceder_a_retiro(self):
        self.comprobar_acceso_permitido(
            self.cajero,
            "retiro"
        )

    # El Cajero puede acceder a las operaciones bancarias.
    def test_cajero_puede_acceder_a_transferencia(self):
        self.comprobar_acceso_permitido(
            self.cajero,
            "transferencia"
        )
    # El Supervisor no puede ejecutar estas operaciones.

    def test_supervisor_no_puede_acceder_a_deposito(self):
        self.comprobar_acceso_denegado(
            self.supervisor,
            "deposito"
        )

    def test_supervisor_no_puede_acceder_a_retiro(self):
        self.comprobar_acceso_denegado(
            self.supervisor,
            "retiro"
        )

    def test_supervisor_no_puede_acceder_a_transferencia(self):
        self.comprobar_acceso_denegado(
            self.supervisor,
            "transferencia"
        )

    # Un usuario sin grupo no puede ejecutar operaciones.

    def test_usuario_sin_grupo_no_puede_acceder_a_deposito(self):
        self.comprobar_acceso_denegado(
            self.usuario_sin_grupo,
            "deposito"
        )

    def test_usuario_sin_grupo_no_puede_acceder_a_retiro(self):
        self.comprobar_acceso_denegado(
            self.usuario_sin_grupo,
            "retiro"
        )

    def test_usuario_sin_grupo_no_puede_acceder_a_transferencia(self):
        self.comprobar_acceso_denegado(
            self.usuario_sin_grupo,
            "transferencia"
        )

    # Los usuarios sin sesión deben ir al inicio de sesión.

    def test_usuario_sin_sesion_no_puede_acceder_a_deposito(self):
        respuesta = self.client.get(reverse("deposito"))
        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_puede_acceder_a_retiro(self):
        respuesta = self.client.get(reverse("retiro"))
        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_sin_sesion_no_puede_acceder_a_transferencia(self):
        respuesta = self.client.get(reverse("transferencia"))
        self.assertEqual(respuesta.status_code, 302)

@skipUnlessDBFeature("has_select_for_update")
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

            def ejecutar_transferencia(numero_destino, cliente_http):
                close_old_connections()

                try:

                    # Ambas solicitudes esperan antes de comenzar.
                    barrera.wait(timeout=10)

                    respuesta = cliente_http.post(
                        self.url,
                        {
                            "origen": self.origen.numero_cuenta,
                            "destino": numero_destino,
                            "monto": "80.00",
                            "idempotency_key": str(uuid.uuid4()),
                        },
                        secure=True,
                        follow=True,
                    )

                    contenido = respuesta.content.decode("utf-8", errors="replace")

                    with bloqueo_resultados:
                        resultados.append({
                            "destino": numero_destino,
                            "status": respuesta.status_code,
                            "redirect_chain": respuesta.redirect_chain,
                            "url_final": respuesta.request.get("PATH_INFO"),
                            "mensaje_exito": (
                                "Transferencia realizada correctamente." in contenido
                            ),
                            "mensaje_rechazo": (
                                "Saldo insuficiente en la cuenta origen." in contenido
                            ),
                            "contenido": contenido[:500],
                        })

                except Exception as error:
                    with bloqueo_resultados:
                        errores.append(repr(error))

                finally:
                    close_old_connections()

            # Preparar las sesiones antes de iniciar la concurrencia.
            cliente_http1 = self.client_class()
            cliente_http1.force_login(self.cajero)

            cliente_http2 = self.client_class()
            cliente_http2.force_login(self.cajero)

            hilos = [
                threading.Thread(
                    target=ejecutar_transferencia,
                    args=(self.destino1.numero_cuenta, cliente_http1),
                ),
                threading.Thread(
                    target=ejecutar_transferencia,
                    args=(self.destino2.numero_cuenta, cliente_http2),
                ),
            ]

            for hilo in hilos:
                hilo.start()

            for hilo in hilos:
                hilo.join(timeout=30)

            print("\n--- DIAGNÓSTICO DE TRANSFERENCIAS ---")

            for resultado in resultados:
                print(resultado)

            print("Errores:", errores)

            print("\n--- RESULTADO FINAL DE LA PRUEBA ---")

            print(
                "Saldo origen:",
                Cuenta.objects.get(
                    numero_cuenta=self.origen.numero_cuenta
                ).saldo
            )

            print(
                "Movimientos registrados:",
                Movimiento.objects.count()
            )

            print(
                "Operaciones registradas:",
                OperacionBancaria.objects.count()
            )

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

            # Verificar que solo se registre una operación de transferencia.
            operaciones = OperacionBancaria.objects.filter(
                usuario=self.cajero,
                tipo="T",
            )

            self.assertEqual(
                operaciones.count(),
                1,
                "Debe registrarse exactamente una transferencia.",
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

            # Verificar que solo se audite la transferencia exitosa.
            auditorias = Auditoria.objects.filter(
                usuario=self.cajero,
                modulo="Movimientos",
                accion="Transferencia",
            )

            self.assertEqual(
                auditorias.count(),
                1,
                "Debe existir exactamente una auditoría de transferencia exitosa.",
            )

            auditoria = auditorias.first()

            self.assertIn(
                "Transferencia de S/ 80.00 de CONC000001 a ",
                auditoria.descripcion,
                "La auditoría debe identificar el importe y la cuenta de origen.",
            )

            self.assertTrue(
                any(
                    destino in auditoria.descripcion
                    for destino in [
                        self.destino1.numero_cuenta,
                        self.destino2.numero_cuenta,
                    ]
                ),
                "La auditoría debe identificar la cuenta destino que recibió el dinero.",
            )

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

            # Deben existir exactamente dos respuestas.
            self.assertEqual(len(resultados), 2)

            # Exactamente una transferencia debe ser exitosa.
            self.assertEqual(
                sum(resultado["mensaje_exito"] for resultado in resultados),
                1,
                "Debe existir exactamente una transferencia exitosa."
            )

            # La otra transferencia debe rechazarse por saldo insuficiente.
            self.assertEqual(
                sum(resultado["mensaje_rechazo"] for resultado in resultados),
                1,
                "Debe existir exactamente un rechazo por saldo insuficiente."
            )

            # Ambas solicitudes deben finalizar correctamente a nivel HTTP.
            self.assertTrue(
                all(resultado["status"] == 200 for resultado in resultados)
            )

class ResumenTransferenciasReportesTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Crear el grupo autorizado para consultar los reportes.
        cls.grupo_supervisor, _ = Group.objects.get_or_create(
            name="Supervisor"
        )

        cls.grupo_admin = Group.objects.create(name="Administrador")

        # Crear el usuario supervisor.
        cls.supervisor = User.objects.create_user(
            username="supervisor_resumen_transferencias",
            password="PruebaSegura2026!"
        )
        cls.supervisor.groups.add(cls.grupo_supervisor)

        # Crear cliente de prueba.
        cls.cliente = Cliente.objects.create(
            dni="88888888",
            nombres="Carlos",
            apellidos="Prueba Reportes",
            fecha_nacimiento="1990-01-15",
            direccion="Direccion de prueba",
            telefono="988888888",
            correo="carlos.reportes@example.com",
            estado="A"
        )

        # Crear cuenta de origen.
        cls.origen = Cuenta.objects.create(
            numero_cuenta="REP0000001",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("800.00"),
            estado="A"
        )

        # Crear cuenta de destino.
        cls.destino = Cuenta.objects.create(
            numero_cuenta="REP0000002",
            cliente=cls.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("700.00"),
            estado="A"
        )

        # Registrar la salida de la transferencia.
        Movimiento.objects.create(
            cuenta=cls.origen,
            tipo="T",
            monto=Decimal("200.00"),
            saldo_anterior=Decimal("1000.00"),
            saldo_actual=Decimal("800.00"),
            descripcion="Transferencia a REP0000002"
        )

        # Registrar la entrada de la misma transferencia.
        Movimiento.objects.create(
            cuenta=cls.destino,
            tipo="T",
            monto=Decimal("200.00"),
            saldo_anterior=Decimal("500.00"),
            saldo_actual=Decimal("700.00"),
            descripcion="Transferencia de REP0000001"
        )

    def setUp(self):
        self.client.force_login(self.supervisor)

    def test_excel_muestra_los_dos_movimientos(self):
        respuesta = self.client.get(
            reverse("reporte_movimientos_excel")
        )

        self.assertEqual(respuesta.status_code, 200)

        from io import BytesIO
        from openpyxl import load_workbook

        libro = load_workbook(
            BytesIO(respuesta.content),
            data_only=True
        )
        hoja = libro["Movimientos"]

        # El resumen debe contabilizar solamente la salida.
        total_encontrado = None

        for fila in hoja.iter_rows():
            if fila[0].value == "Total de transferencias:":
                total_encontrado = fila[4].value
                break

        self.assertIsNotNone(
            total_encontrado,
            "No se encontró el total de transferencias en el Excel."
        )

        self.assertEqual(
            Decimal(str(total_encontrado)),
            Decimal("200.00")
        )

        # Verificar que ambos movimientos estén en el reporte.
        self.assertEqual(Movimiento.objects.filter(tipo="T").count(), 2)
    def test_pdf_muestra_el_total_correcto_de_transferencias(self):
        from io import BytesIO
        from pypdf import PdfReader

        respuesta = self.client.get(
            reverse("reporte_movimientos_pdf")
        )

        self.assertEqual(respuesta.status_code, 200)

        lector = PdfReader(BytesIO(respuesta.content))

        texto_pdf = "\n".join(
            pagina.extract_text() or ""
            for pagina in lector.pages
        )

        self.assertIn(
            "Total transferencias: S/ 200.00",
            texto_pdf
        )

class ProteccionEliminacionTests(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            dni="76543210",
            nombres="Cliente",
            apellidos="Proteccion",
            fecha_nacimiento="1990-01-15",
            direccion="Lima",
            telefono="987654321",
            correo="proteccion@example.com",
            estado="A",
        )

        self.cuenta = Cuenta.objects.create(
            numero_cuenta="PROT000001",
            cliente=self.cliente,
            tipo_cuenta="AH",
            saldo=Decimal("100.00"),
            estado="A",
        )

        self.movimiento = Movimiento.objects.create(
            cuenta=self.cuenta,
            tipo="D",
            monto=Decimal("10.00"),
            saldo_anterior=Decimal("90.00"),
            saldo_actual=Decimal("100.00"),
            descripcion="Movimiento de prueba",
        )

    def test_no_permite_eliminar_cuenta_con_movimientos(self):
        with self.assertRaises(ProtectedError):
            self.cuenta.delete()

        self.assertTrue(Cuenta.objects.filter(pk=self.cuenta.pk).exists())
        self.assertTrue(Movimiento.objects.filter(pk=self.movimiento.pk).exists())

    def test_no_permite_eliminar_cliente_con_cuentas(self):
        with self.assertRaises(ProtectedError):
            self.cliente.delete()

        self.assertTrue(Cliente.objects.filter(pk=self.cliente.pk).exists())
        self.assertTrue(Cuenta.objects.filter(pk=self.cuenta.pk).exists())
        self.assertTrue(Movimiento.objects.filter(pk=self.movimiento.pk).exists())

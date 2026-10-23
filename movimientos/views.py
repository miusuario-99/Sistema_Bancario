from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from cuentas.models import Cuenta
from .models import Movimiento
from decimal import Decimal, InvalidOperation
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from usuarios.decorators import grupos_permitidos
from auditoria.utils import registrar_auditoria
from django.db.models import Sum

@grupos_permitidos("Administrador", "Cajero")
def deposito(request):

    if request.method == "POST":

        numero_cuenta = request.POST.get("numero_cuenta", "").strip()
        monto_texto = request.POST.get("monto", "").strip()

        if not numero_cuenta:
            messages.error(request, "Debe ingresar el número de cuenta.")
            return redirect("deposito")

        if not monto_texto:
            messages.error(request, "Debe ingresar el monto.")
            return redirect("deposito")

        try:
            monto = Decimal(monto_texto.replace(",", "."))
        except (InvalidOperation, ValueError):
            messages.error(request, "El monto no es válido.")
            return redirect("deposito")

        # Rechazar NaN e infinito
        if not monto.is_finite():
            messages.error(request, "El monto debe ser un número válido.")
            return redirect("deposito")

        # Rechazar cero y valores negativos
        if monto <= 0:
            messages.error(
                request,
                "El monto debe ser mayor que cero."
            )
            return redirect("deposito")

        # Máximo dos decimales
        if monto.as_tuple().exponent < -2:
            messages.error(
                request,
                "El monto no puede tener más de dos decimales."
            )
            return redirect("deposito")

        # Limitar el monto para evitar importes excesivos
        if monto >= Decimal("10000000000"):
            messages.error(
                request,
                "El monto supera el límite permitido."
            )
            return redirect("deposito")


        try:
            with transaction.atomic():

                cuenta = Cuenta.objects.select_for_update().get(
                    numero_cuenta=numero_cuenta
                )

                if cuenta.estado != "A":

                    messages.error(
                        request,
                        "La cuenta no está activa."
                    )

                    return redirect("deposito")

                saldo_maximo = Decimal("9999999999.99")

                if cuenta.saldo + monto > saldo_maximo:
                    messages.error(
                        request,
                        "La operación supera el saldo máximo permitido."
                    )
                    return redirect("deposito")

                saldo_anterior = cuenta.saldo
                cuenta.saldo += monto
                cuenta.save(update_fields=["saldo"])

                Movimiento.objects.create(
                    cuenta=cuenta,
                    tipo='D',
                    monto=monto,
                    saldo_anterior=saldo_anterior,
                    saldo_actual=cuenta.saldo,
                    descripcion="Depósito en efectivo"
                )

                registrar_auditoria(
                    request,
                    "Movimientos",
                    "Depósito",
                    f"Depósito de S/ {monto:.2f} en cuenta {cuenta.numero_cuenta}"
                )

                messages.success(request, "Depósito realizado correctamente.")
                return redirect("deposito")

        except Cuenta.DoesNotExist:
            messages.error(request, "La cuenta no existe.")

    return render(request, "movimientos/deposito.html")

@grupos_permitidos("Administrador", "Cajero")
def retiro(request):

    if request.method == "POST":

        numero_cuenta = (
            request.POST.get("numero_cuenta", "").strip()
        )

        # 1. Validar el número de cuenta
        if not numero_cuenta:
            messages.error(
                request,
                "Debe ingresar el número de cuenta."
            )
            return redirect("retiro")

        # 2. Validar el monto ingresado
        monto_texto = (
            request.POST.get("monto", "").strip()
        ).replace(",", ".")

        try:
            monto = Decimal(monto_texto)

        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Ingrese un monto válido."
            )
            return redirect("retiro")

        # 3. Rechazar valores no válidos
        if not monto.is_finite():
            messages.error(
                request,
                "El monto debe ser un número válido."
            )
            return redirect("retiro")

        if monto <= 0:
            messages.error(
                request,
                "El monto debe ser mayor que cero."
            )
            return redirect("retiro")

        if monto.as_tuple().exponent < -2:
            messages.error(
                request,
                "El monto no puede tener más de dos decimales."
            )
            return redirect("retiro")

        if monto >= Decimal("10000000000"):
            messages.error(
                request,
                "El monto supera el límite permitido."
            )
            return redirect("retiro")

        # 4. Procesar el retiro dentro de una transacción
        try:
            with transaction.atomic():

                cuenta = Cuenta.objects.select_for_update().get(
                    numero_cuenta=numero_cuenta
                )

                # Verificar que la cuenta esté activa
                if cuenta.estado != "A":
                    messages.error(
                        request,
                        "La cuenta no está activa."
                    )
                    return redirect("retiro")

                # Verificar que exista saldo suficiente
                if cuenta.saldo < monto:
                    messages.error(
                        request,
                        "Saldo insuficiente."
                    )
                    return redirect("retiro")

                # Guardar el saldo anterior
                saldo_anterior = cuenta.saldo

                # Actualizar el saldo
                cuenta.saldo -= monto
                cuenta.save(update_fields=["saldo"])

                # Registrar el movimiento
                Movimiento.objects.create(
                    cuenta=cuenta,
                    tipo="R",
                    monto=monto,
                    saldo_anterior=saldo_anterior,
                    saldo_actual=cuenta.saldo,
                    descripcion="Retiro en efectivo"
                )

                # Registrar la auditoría
                registrar_auditoria(
                    request,
                    "Movimientos",
                    "Retiro",
                    (
                        f"Retiro de S/ {monto:.2f} "
                        f"de cuenta {cuenta.numero_cuenta}"
                    )
                )

                messages.success(
                    request,
                    "Retiro realizado correctamente."
                )
                return redirect("retiro")

        except Cuenta.DoesNotExist:
            messages.error(
                request,
                "La cuenta no existe."
            )

    return render(request, "movimientos/retiro.html")

@grupos_permitidos("Administrador", "Cajero")
def transferencia(request):

    if request.method == "POST":

        origen_num = request.POST.get("origen", "").strip()
        destino_num = request.POST.get("destino", "").strip()

        # 1. Validar las cuentas ingresadas
        if not origen_num or not destino_num:
            messages.error(
                request,
                "Debe ingresar las cuentas de origen y destino."
            )
            return redirect("transferencia")

        if origen_num == destino_num:
            messages.error(
                request,
                "La cuenta origen y destino no pueden ser la misma."
            )
            return redirect("transferencia")

        # 2. Validar el monto
        monto_texto = (
            request.POST.get("monto", "").strip()
        ).replace(",", ".")

        try:
            monto = Decimal(monto_texto)

        except (InvalidOperation, ValueError):
            messages.error(
                request,
                "Ingrese un monto válido."
            )
            return redirect("transferencia")

        if not monto.is_finite():
            messages.error(
                request,
                "El monto debe ser un número válido."
            )
            return redirect("transferencia")

        if monto <= 0:
            messages.error(
                request,
                "El monto debe ser mayor que cero."
            )
            return redirect("transferencia")

        if monto.as_tuple().exponent < -2:
            messages.error(
                request,
                "El monto no puede tener más de dos decimales."
            )
            return redirect("transferencia")

        if monto >= Decimal("10000000000"):
            messages.error(
                request,
                "El monto supera el límite permitido."
            )
            return redirect("transferencia")

        # 3. Procesar la transferencia de forma atómica
        try:
            with transaction.atomic():

                # Bloquear las cuentas siempre en el mismo orden
                cuentas_bloqueadas = {}

                for numero in sorted([origen_num, destino_num]):
                    cuenta = Cuenta.objects.select_for_update().get(
                        numero_cuenta=numero
                    )
                    cuentas_bloqueadas[numero] = cuenta

                # Recuperar las cuentas según el sentido de la transferencia
                origen = cuentas_bloqueadas[origen_num]
                destino = cuentas_bloqueadas[destino_num]

                # 4. Verificar que ambas cuentas estén activas
                if origen.estado != "A":
                    messages.error(
                        request,
                        "La cuenta origen está inactiva."
                    )
                    return redirect("transferencia")

                if destino.estado != "A":
                    messages.error(
                        request,
                        "La cuenta destino está inactiva."
                    )
                    return redirect("transferencia")

                # 5. Verificar el saldo de origen
                if origen.saldo < monto:
                    messages.error(
                        request,
                        "Saldo insuficiente en la cuenta origen."
                    )
                    return redirect("transferencia")

                # Verificar que el saldo destino no supere el máximo permitido
                saldo_maximo = Decimal("9999999999.99")

                if destino.saldo + monto > saldo_maximo:
                    messages.error(
                        request,
                        "La operación supera el saldo máximo permitido en la cuenta destino."
                    )
                    return redirect("transferencia")

                # 6. Descontar el monto de la cuenta origen
                saldo_origen_anterior = origen.saldo
                origen.saldo -= monto
                origen.save(update_fields=["saldo"])

                Movimiento.objects.create(
                    cuenta=origen,
                    tipo="T",
                    monto=monto,
                    saldo_anterior=saldo_origen_anterior,
                    saldo_actual=origen.saldo,
                    descripcion=(
                        f"Transferencia a {destino.numero_cuenta}"
                    )
                )

                # 7. Abonar el monto a la cuenta destino
                saldo_destino_anterior = destino.saldo
                destino.saldo += monto
                destino.save(update_fields=["saldo"])

                Movimiento.objects.create(
                    cuenta=destino,
                    tipo="T",
                    monto=monto,
                    saldo_anterior=saldo_destino_anterior,
                    saldo_actual=destino.saldo,
                    descripcion=(
                        f"Transferencia desde {origen.numero_cuenta}"
                    )
                )

                # 8. Registrar la operación en auditoría
                registrar_auditoria(
                    request,
                    "Movimientos",
                    "Transferencia",
                    (
                        f"Transferencia de S/ {monto:.2f} "
                        f"de {origen.numero_cuenta} "
                        f"a {destino.numero_cuenta}"
                    )
                )

                messages.success(
                    request,
                    "Transferencia realizada correctamente."
                )
                return redirect("transferencia")

        except Cuenta.DoesNotExist:
            messages.error(
                request,
                "La cuenta de origen o destino no existe."
            )

    return render(request, "movimientos/transferencia.html")

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def historial(request):
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    tipo = request.GET.get("tipo")

    movimientos = Movimiento.objects.select_related(
        "cuenta",
        "cuenta__cliente"
    )

    # Filtrar por fecha inicial.
    if fecha_inicio:
        movimientos = movimientos.filter(
            fecha__date__gte=fecha_inicio
        )

    # Filtrar por fecha final.
    if fecha_fin:
        movimientos = movimientos.filter(
            fecha__date__lte=fecha_fin
        )

    # Filtrar por tipo de movimiento.
    if tipo in ("D", "R", "T"):
        movimientos = movimientos.filter(tipo=tipo)

    movimientos = movimientos.order_by("-fecha")

    puede_exportar = request.user.groups.filter(
        name__in=["Administrador", "Supervisor"]
    ).exists()

    return render(request, "movimientos/historial.html", {
        "movimientos": movimientos,
        "puede_exportar": puede_exportar,
    })

@grupos_permitidos("Administrador", "Supervisor")
def reporte_movimientos_pdf(request):

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    tipo = request.GET.get("tipo")

    movimientos = Movimiento.objects.select_related(
        "cuenta",
        "cuenta__cliente"
    )

    # Aplicar filtro por fecha inicial.
    if fecha_inicio:
        movimientos = movimientos.filter(
            fecha__date__gte=fecha_inicio
        )

    # Aplicar filtro por fecha final.
    if fecha_fin:
        movimientos = movimientos.filter(
            fecha__date__lte=fecha_fin
        )

    # Aplicar filtro por tipo de movimiento.
    if tipo in ("D", "R", "T"):
        movimientos = movimientos.filter(tipo=tipo)

    movimientos = movimientos.order_by("-fecha")

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        'attachment; filename="reporte_movimientos.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)

    ANCHO, ALTO = A4

    # ==========================
    # CABECERA
    # ==========================

    logo = os.path.join(
        settings.BASE_DIR,
        "static",
        "img",
        "logo_banco.png"
    )

    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.rect(
        0,
        ALTO - 0.5 * cm,
        ANCHO,
        0.5 * cm,
        fill=1,
        stroke=0
    )

    try:
        pdf.drawImage(
            logo,
            2 * cm,
            ALTO - 3.2 * cm,
            width=2.2 * cm,
            height=2.2 * cm,
            preserveAspectRatio=True,
            mask="auto"
        )
    except:
        pass

    pdf.setFillColor(colors.HexColor("#0B3A75"))
    pdf.setFont("Helvetica-Bold", 22)

    pdf.drawString(
        5 * cm,
        ALTO - 1.8 * cm,
        "BANCO PYTHON"
    )

    pdf.setFont("Helvetica", 11)
    pdf.setFillColor(colors.grey)

    pdf.drawString(
        5 * cm,
        ALTO - 2.5 * cm,
        "Tecnología • Seguridad • Confianza"
    )

    pdf.setFillColor(colors.black)

    pdf.setFont("Helvetica", 9)

    pdf.drawRightString(
        19 * cm,
        ALTO - 1.8 * cm,
        f"Emitido: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    pdf.setStrokeColor(colors.HexColor("#0B3A75"))

    pdf.line(
        2 * cm,
        ALTO - 3.6 * cm,
        19 * cm,
        ALTO - 3.6 * cm
    )

    pdf.setFont("Helvetica-Bold", 18)

    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.drawCentredString(
    ANCHO / 2,
    ALTO - 4.2 * cm,
    "REPORTE GENERAL DE MOVIMIENTOS"
    )

    # ======================================
    # TABLA
    # ======================================

    y = ALTO - 6.5 * cm

    alto_fila = 0.7 * cm

    x1 = 1.5 * cm   # Cuenta
    x2 = 4.5 * cm   # Cliente
    x3 = 9.0 * cm   # Tipo
    x4 = 12.0 * cm  # Monto
    x5 = 15.0 * cm  # Fecha
    x6 = 18.5 * cm

    def dibujar_pie_pagina(numero_pagina):
        pdf.setStrokeColor(colors.HexColor("#0B3A75"))
        pdf.line(2 * cm, 1.5 * cm, 19 * cm, 1.5 * cm)

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.grey)

        pdf.drawString(
            2 * cm,
            1 * cm,
            "Banco Python - Reporte generado automáticamente"
        )

        pdf.drawRightString(
            19 * cm,
            1 * cm,
            f"Página {numero_pagina}"
        )


    def dibujar_encabezado_tabla(y_tabla):
        pdf.setFillColor(colors.HexColor("#0B3A75"))
        pdf.rect(
            x1,
            y_tabla,
            x6 - x1,
            alto_fila,
            fill=1,
            stroke=1
        )

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 9)

        pdf.drawCentredString(3 * cm, y_tabla + 0.22 * cm, "Cuenta")
        pdf.drawCentredString(6.7 * cm, y_tabla + 0.22 * cm, "Cliente")
        pdf.drawCentredString(10.5 * cm, y_tabla + 0.22 * cm, "Tipo")
        pdf.drawCentredString(13.5 * cm, y_tabla + 0.22 * cm, "Monto")
        pdf.drawCentredString(16.7 * cm, y_tabla + 0.22 * cm, "Fecha")

    # ======================================
    # FILAS DE MOVIMIENTOS CON PAGINACIÓN
    # ======================================

    numero_pagina = 1
    y = ALTO - 6.5 * cm

    dibujar_encabezado_tabla(y)
    y -= alto_fila

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    # Reservar espacio para el pie de página.
    limite_inferior = 3 * cm

    # Si no cabe otra fila, pasar a la página siguiente.
    for mov in movimientos:

            print("MOVIMIENTO:", mov.id, mov.cuenta.numero_cuenta, "Y:", y)

            # Si no cabe otra fila, pasar a la página siguiente.
            if y < limite_inferior:
                dibujar_pie_pagina(numero_pagina)
                pdf.showPage()
                numero_pagina += 1

                # Reiniciar posición y estilos.
                y = ALTO - 3 * cm

                # Dibujar encabezado en la nueva página.
                dibujar_encabezado_tabla(y)
                y -= alto_fila

                pdf.setFillColor(colors.black)
                pdf.setFont("Helvetica", 8)


            # Número de cuenta.
            pdf.drawCentredString(
                3 * cm,
                y,
                mov.cuenta.numero_cuenta
            )

            # Nombre del cliente.
            nombre_cliente = (
                f"{mov.cuenta.cliente.nombres} "
                f"{mov.cuenta.cliente.apellidos}"
            )

            pdf.drawString(
                5.5 * cm,
                y,
                nombre_cliente[:30]
            )

            # Tipo de movimiento.
            pdf.drawString(
                10.2 * cm,
                y,
                mov.get_tipo_display()
            )

            # Monto.
            pdf.drawCentredString(
                13.5 * cm,
                y,
                f"S/ {mov.monto:.2f}"
            )

            # Fecha.
            pdf.drawCentredString(
                16.7 * cm,
                y,
                mov.fecha.strftime("%d/%m/%Y")
            )

            # Línea separadora.
            pdf.setStrokeColor(colors.lightgrey)
            pdf.line(
                x1,
                y - 0.1 * cm,
                x6,
                y - 0.1 * cm
            )

            # Posición para la siguiente fila.
            y -= alto_fila

    # ======================================
    # RESUMEN DE MOVIMIENTOS
    # ======================================

    total_depositos = movimientos.filter(
        tipo="D"
    ).aggregate(total=Sum("monto"))["total"] or 0

    total_retiros = movimientos.filter(
        tipo="R"
    ).aggregate(total=Sum("monto"))["total"] or 0

    total_transferencias = movimientos.filter(
        tipo="T"
    ).aggregate(total=Sum("monto"))["total"] or 0

    # Si no hay espacio para el resumen, iniciar una página
    # nueva SIN dibujar el encabezado de la tabla.
    if y < 5 * cm:
        dibujar_pie_pagina(numero_pagina)
        pdf.showPage()
        numero_pagina += 1
        y = ALTO - 3 * cm

    y -= 0.5 * cm

    pdf.setStrokeColor(colors.HexColor("#0B3A75"))
    pdf.line(2 * cm, y, 19 * cm, y)

    y -= 0.8 * cm

    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.HexColor("#0B3A75"))
    pdf.drawString(2 * cm, y, "RESUMEN DE MOVIMIENTOS")

    y -= 0.6 * cm

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.black)

    pdf.drawString(
        2 * cm, y,
        f"Total depósitos: S/ {total_depositos:,.2f}"
    )

    y -= 0.5 * cm

    pdf.drawString(
        2 * cm, y,
        f"Total retiros: S/ {total_retiros:,.2f}"
    )

    y -= 0.5 * cm

    pdf.drawString(
        2 * cm, y,
        f"Total transferencias: S/ {total_transferencias:,.2f}"
    )

    # Pie de la última página.
    dibujar_pie_pagina(numero_pagina)

    pdf.save()
    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_movimientos_excel(request):

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    tipo = request.GET.get("tipo")

    movimientos = Movimiento.objects.select_related(
        "cuenta",
        "cuenta__cliente"
    )

    # Filtrar por fecha inicial.
    if fecha_inicio:
        movimientos = movimientos.filter(
            fecha__date__gte=fecha_inicio
        )

    # Filtrar por fecha final.
    if fecha_fin:
        movimientos = movimientos.filter(
            fecha__date__lte=fecha_fin
        )

    # Filtrar por tipo de movimiento.
    if tipo in ("D", "R", "T"):
        movimientos = movimientos.filter(tipo=tipo)

    movimientos = movimientos.order_by("-fecha")

    # Crear libro y hoja de Excel.
    wb = Workbook()
    ws = wb.active
    ws.title = "Movimientos"

    # Título del reporte.
    ws.merge_cells("A1:H1")
    ws["A1"] = "BANCO PYTHON - REPORTE DE MOVIMIENTOS"
    ws["A1"].font = Font(
        bold=True,
        color="FFFFFF",
        size=14
    )
    ws["A1"].fill = PatternFill(
        fill_type="solid",
        fgColor="0B3A75"
    )
    ws["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )
    ws.row_dimensions[1].height = 30

    # Fecha de emisión.
    ws.merge_cells("A2:H2")
    ws["A2"] = (
        f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    ws["A2"].alignment = Alignment(horizontal="right")

    # Encabezados.
    encabezados = [
        "Fecha",
        "Cuenta",
        "Cliente",
        "Tipo",
        "Monto",
        "Saldo Anterior",
        "Saldo Actual",
        "Descripción"
    ]

    for col, encabezado in enumerate(encabezados, start=1):
        celda = ws.cell(row=4, column=col, value=encabezado)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill(
            fill_type="solid",
            fgColor="0B3A75"
        )
        celda.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # Registrar movimientos.
    fila = 5

    for m in movimientos:
        ws.cell(
            row=fila,
            column=1,
            value=m.fecha.strftime("%d/%m/%Y %H:%M")
        )
        ws.cell(row=fila, column=2, value=m.cuenta.numero_cuenta)
        ws.cell(
            row=fila,
            column=3,
            value=(
                f"{m.cuenta.cliente.nombres} "
                f"{m.cuenta.cliente.apellidos}"
            )
        )
        ws.cell(row=fila, column=4, value=m.get_tipo_display())

        # Importes numéricos para permitir cálculos en Excel.
        ws.cell(row=fila, column=5, value=float(m.monto))
        ws.cell(row=fila, column=6, value=float(m.saldo_anterior))
        ws.cell(row=fila, column=7, value=float(m.saldo_actual))
        ws.cell(row=fila, column=8, value=m.descripcion)

        # Formato monetario.
        for columna in (5, 6, 7):
            ws.cell(row=fila, column=columna).number_format = '"S/ " #,##0.00'

        fila += 1

    # Totales por tipo de movimiento.
    total_depositos = movimientos.filter(
        tipo="D"
    ).aggregate(total=Sum("monto"))["total"] or 0

    total_retiros = movimientos.filter(
        tipo="R"
    ).aggregate(total=Sum("monto"))["total"] or 0

    total_transferencias = movimientos.filter(
        tipo="T"
    ).aggregate(total=Sum("monto"))["total"] or 0

    # Resumen al final.
    fila_resumen = fila + 1

    ws.cell(row=fila_resumen, column=1, value="RESUMEN DE MOVIMIENTOS")
    ws.cell(
        row=fila_resumen,
        column=1
    ).font = Font(bold=True, color="FFFFFF")
    ws.cell(
        row=fila_resumen,
        column=1
    ).fill = PatternFill(fill_type="solid", fgColor="0B3A75")

    ws.merge_cells(
        start_row=fila_resumen,
        start_column=1,
        end_row=fila_resumen,
        end_column=4
    )

    resumen = [
        ("Total de movimientos:", movimientos.count()),
        ("Total de depósitos:", total_depositos),
        ("Total de retiros:", total_retiros),
        ("Total de transferencias:", total_transferencias),
    ]

    for desplazamiento, (etiqueta, valor) in enumerate(resumen, start=1):
        r = fila_resumen + desplazamiento

        ws.cell(row=r, column=1, value=etiqueta)
        ws.cell(row=r, column=5, value=float(valor) if desplazamiento > 1 else valor)

        if desplazamiento > 1:
            ws.cell(row=r, column=5).number_format = '"S/ " #,##0.00'

        ws.cell(row=r, column=1).font = Font(bold=True)

    # Ancho de columnas.
    anchos = {
        "A": 22,
        "B": 16,
        "C": 32,
        "D": 18,
        "E": 16,
        "F": 18,
        "G": 18,
        "H": 38,
    }

    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho

    # Fijar encabezados al desplazarse por el reporte.
    ws.freeze_panes = "A5"

    # Activar filtros en los movimientos.
    if fila > 5:
        ws.auto_filter.ref = f"A4:H{fila - 1}"

    # Configurar impresión horizontal.
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    # Descargar archivo.
    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="movimientos.xlsx"'
    )

    wb.save(response)

    return response
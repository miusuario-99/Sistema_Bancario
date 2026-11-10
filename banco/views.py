from django.shortcuts import render, get_object_or_404
from movimientos.models import Movimiento
from clientes.models import Cliente
from cuentas.models import Cuenta
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
from reportlab.lib import colors
import os
from django.conf import settings
from reportlab.lib.pagesizes import A4
from django.db.models import Sum, Count, Avg, Max, Min
from django.db.models.functions import TruncDate
from django.db.models.functions import TruncMonth
from django.utils import timezone
from usuarios.decorators import grupos_permitidos

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def dashboard(request):

    total_clientes = Cliente.objects.count()
    total_cuentas = Cuenta.objects.count()

    saldo_total = Cuenta.objects.aggregate(
        total=Sum("saldo")
    )["total"] or 0

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    movimientos = (
    Movimiento.objects
    .select_related("cuenta", "cuenta__cliente")
)

    if fecha_inicio:
        movimientos = movimientos.filter(fecha__date__gte=fecha_inicio)

    if fecha_fin:
        movimientos = movimientos.filter(fecha__date__lte=fecha_fin)

    # ===========================
    # ESTADÍSTICAS
    # ===========================

    total_movimientos = movimientos.count()

    depositos = movimientos.filter(tipo="D").count()

    retiros = movimientos.filter(tipo="R").count()

    transferencias = movimientos.filter(tipo="T").count()

    # ===========================
    # TOTALES POR TIPO
    # ===========================

    total_depositos = (
        movimientos.filter(tipo="D")
        .aggregate(total=Sum("monto"))["total"] or 0
    )

    total_retiros = (
        movimientos.filter(tipo="R")
        .aggregate(total=Sum("monto"))["total"] or 0
    )

    total_transferencias = (
        movimientos.filter(tipo="T")
        .aggregate(total=Sum("monto"))["total"] or 0
    )

    promedio_movimiento = (
        movimientos.aggregate(promedio=Avg("monto"))["promedio"] or 0
    )

    # ===========================
    # GRÁFICO DE LÍNEAS
    # ===========================

    # Datos para gráfico circular

    tipos_movimientos = (
        movimientos
        .values("tipo")
        .annotate(total=Count("id"))
    )


    tipos = []
    cantidades = []


    TIPOS = {
        "D": "Depósitos",
        "R": "Retiros",
        "T": "Transferencias",
    }

    for t in tipos_movimientos:
        tipos.append(TIPOS.get(t["tipo"], t["tipo"]))
        cantidades.append(t["total"])

    movimientos_fecha = (
        movimientos
        .annotate(fecha_dia=TruncDate("fecha"))
        .values("fecha_dia")
        .annotate(total=Sum("monto"))
        .order_by("fecha_dia")
    )

    fechas = []
    montos = []

    for item in movimientos_fecha:
        fechas.append(
        item["fecha_dia"].strftime("%d/%m/%Y")
    )

        montos.append(
        float(item["total"])
    )


    # ===========================
    # GRÁFICO DE BARRAS
    # Movimientos por mes
    # ===========================

    movimientos_mes = (
        movimientos
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    meses = []
    totales_mes = []

    for item in movimientos_mes:
        meses.append(item["mes"].strftime("%b %Y"))
        totales_mes.append(float(item["total"]))

    ultimos_movimientos = (
    movimientos.select_related("cuenta")
    .order_by("-fecha")[:5]
    )

    fecha_actual = timezone.now()

    # ==========================================
    # DEPÓSITOS VS RETIROS POR MES
    # ==========================================

    depositos_mes = (
        movimientos
        .filter(tipo="D")
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    retiros_mes = (
        movimientos
        .filter(tipo="R")
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    # Diccionario con todos los meses
    datos = {}

    for item in depositos_mes:
        datos[item["mes"]] = {
            "depositos": float(item["total"]),
            "retiros": 0
        }

    for item in retiros_mes:

        if item["mes"] not in datos:

            datos[item["mes"]] = {
                "depositos": 0,
                "retiros": float(item["total"])
            }

        else:

            datos[item["mes"]]["retiros"] = float(item["total"])

    meses_finanzas = []
    depositos_totales = []
    retiros_totales = []

    for mes in sorted(datos.keys()):

        meses_finanzas.append(mes.strftime("%b %Y"))
        depositos_totales.append(datos[mes]["depositos"])
        retiros_totales.append(datos[mes]["retiros"])

    # ===========================
    # TOP 5 CUENTAS CON MAYOR SALDO
    # ===========================

    top_cuentas = (
        Cuenta.objects
        .select_related("cliente")
        .order_by("-saldo")[:5]
    )

    # ==========================================
    # INDICADORES EJECUTIVOS
    # ==========================================

    mayor_saldo = (
        Cuenta.objects.aggregate(maximo=Max("saldo"))["maximo"] or 0
    )

    menor_saldo = (
        Cuenta.objects.aggregate(minimo=Min("saldo"))["minimo"] or 0
    )

    saldo_promedio = (
        Cuenta.objects.aggregate(promedio=Avg("saldo"))["promedio"] or 0
    )

    cliente_mas_cuentas = (
        Cliente.objects
        .annotate(total_cuentas=Count("cuentas"))
        .order_by("-total_cuentas")
        .first()
    )

    contexto = {

        "total_clientes": total_clientes,
        "total_cuentas": total_cuentas,
        "saldo_total": saldo_total,
         "fecha_actual": fecha_actual,
        "total_movimientos": total_movimientos,
        "depositos": depositos,
        "retiros": retiros,
        "transferencias": transferencias,
        "ultimos_movimientos": ultimos_movimientos,
        "top_cuentas": top_cuentas,
        "total_depositos": total_depositos,
        "total_retiros": total_retiros,
        "total_transferencias": total_transferencias,
        "promedio_movimiento": promedio_movimiento,
        "mayor_saldo": mayor_saldo,
        "menor_saldo": menor_saldo,
        "saldo_promedio": saldo_promedio,
        "cliente_mas_cuentas": cliente_mas_cuentas,
        "meses_finanzas": meses_finanzas,
        "depositos_totales": depositos_totales,
        "retiros_totales": retiros_totales,

        # gráfico líneas
        "fechas_movimientos": fechas,
        "montos_movimientos": montos,

        # gráfico distribución
        "tipos": tipos,
        "cantidades": cantidades,
        "meses": meses,
        "totales_mes": totales_mes,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,

    }

    return render(request, "dashboard.html", contexto)

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def estado_cuenta(request):

    cuentas = Cuenta.objects.all()

    return render(
        request,
        "estado_cuenta.html",
        {
            "cuentas": cuentas
        }
    )

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def estado_cuenta_pdf(request, cuenta_id):

    cuenta = get_object_or_404(
        Cuenta.objects.select_related("cliente"),
        id=cuenta_id
    )

    movimientos = list(
        Movimiento.objects
        .filter(cuenta=cuenta)
        .order_by("fecha", "id")
    )

    # ==========================================
    # CONFIGURACIÓN DEL DOCUMENTO
    # ==========================================

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="estado_cuenta_{cuenta.numero_cuenta}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)

    ANCHO, ALTO = A4

    margen_izquierdo = 2 * cm
    margen_derecho = 19 * cm
    ancho_tabla = margen_derecho - margen_izquierdo

    azul = colors.HexColor("#0B3A75")

    # ==========================================
    # DATOS DEL RESUMEN
    # ==========================================

    total_depositos = sum(
    m.monto for m in movimientos
    if m.tipo == "D"
)

    total_retiros = sum(
        m.monto for m in movimientos
        if m.tipo == "R"
    )

    transferencias_recibidas = sum(
        m.monto for m in movimientos
        if m.tipo == "T"
        and (m.descripcion or "").startswith("Transferencia desde ")
    )

    transferencias_enviadas = sum(
        m.monto for m in movimientos
        if m.tipo == "T"
        and (m.descripcion or "").startswith("Transferencia a ")
    )

    # ==========================================
    # ENCABEZADO GENERAL
    # ==========================================

    def dibujar_encabezado():

        pdf.setFillColor(azul)
        pdf.rect(
            0,
            ALTO - 0.5 * cm,
            ANCHO,
            0.5 * cm,
            fill=1,
            stroke=0
        )

        # Logotipo: solo se omite si no se puede cargar.
        logo = os.path.join(
            settings.BASE_DIR,
            "static",
            "img",
            "logo_banco.png"
        )

        if os.path.isfile(logo):
            try:
                pdf.drawImage(
                    logo,
                    1.8 * cm,
                    ALTO - 3.0 * cm,
                    width=2 * cm,
                    height=2 * cm,
                    preserveAspectRatio=True,
                    mask="auto"
                )
            except (OSError, ValueError):
                pass

        pdf.setFillColor(azul)
        pdf.setFont("Helvetica-Bold", 22)
        pdf.drawString(
            5 * cm,
            ALTO - 1.8 * cm,
            "BANCO PYTHON"
        )

        pdf.setFillColor(colors.grey)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(
            5 * cm,
            ALTO - 2.5 * cm,
            "Tecnología • Seguridad • Confianza"
        )

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(
            margen_derecho,
            ALTO - 1.7 * cm,
            f"Emitido: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

        pdf.setStrokeColor(azul)
        pdf.setLineWidth(1)
        pdf.line(
            margen_izquierdo,
            ALTO - 3.6 * cm,
            margen_derecho,
            ALTO - 3.6 * cm
        )

        pdf.setFont("Helvetica-Bold", 18)
        pdf.setFillColor(azul)
        pdf.drawCentredString(
            ANCHO / 2,
            ALTO - 4.4 * cm,
            "ESTADO DE CUENTA BANCARIO"
        )

    # ==========================================
    # PIE DE PÁGINA
    # ==========================================

    def dibujar_pie_pagina(numero_pagina):

        pdf.setStrokeColor(azul)
        pdf.setLineWidth(0.8)

        pdf.line(
            margen_izquierdo,
            1.8 * cm,
            margen_derecho,
            1.8 * cm
        )

        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica-Oblique", 8)

        pdf.drawCentredString(
            ANCHO / 2,
            1.3 * cm,
            "Documento generado automáticamente por el Sistema Bancario"
        )

        pdf.drawRightString(
            margen_derecho,
            0.7 * cm,
            f"Página {numero_pagina}"
        )

    # ==========================================
    # ENCABEZADO DE LA TABLA
    # ==========================================

    alto_fila = 0.80 * cm

    x1 = 2.0 * cm
    x2 = 4.8 * cm
    x3 = 7.5 * cm
    x4 = 13.0 * cm
    x5 = 16.0 * cm
    x6 = 19.0 * cm

    def dibujar_encabezado_tabla(y):

        pdf.setFillColor(azul)
        pdf.rect(
            x1,
            y,
            x6 - x1,
            alto_fila,
            fill=1,
            stroke=1
        )

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 8)

        pdf.drawCentredString(
            (x1 + x2) / 2,
            y + 0.28 * cm,
            "Fecha"
        )

        pdf.drawCentredString(
            (x2 + x3) / 2,
            y + 0.28 * cm,
            "Tipo"
        )

        pdf.drawCentredString(
            (x3 + x4) / 2,
            y + 0.28 * cm,
            "Descripción"
        )

        pdf.drawCentredString(
            (x4 + x5) / 2,
            y + 0.28 * cm,
            "Monto"
        )

        pdf.drawCentredString(
            (x5 + x6) / 2,
            y + 0.28 * cm,
            "Saldo"
        )

        return y - alto_fila

    # ==========================================
    # PRIMERA PÁGINA: CLIENTE Y CUENTA
    # ==========================================

    numero_pagina = 1

    dibujar_encabezado()

    y = ALTO - 6.2 * cm

    pdf.setStrokeColor(azul)
    pdf.setFillColor(colors.white)

    pdf.roundRect(
        margen_izquierdo,
        y - 2.8 * cm,
        ancho_tabla,
        2.8 * cm,
        8,
        fill=1,
        stroke=1
    )

    pdf.setFillColor(azul)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(
        2.3 * cm,
        y - 0.4 * cm,
        "DATOS DEL CLIENTE"
    )

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        2.5 * cm,
        y - 1.0 * cm,
        f"Cliente: {cuenta.cliente}"
    )

    pdf.drawString(
        2.5 * cm,
        y - 1.6 * cm,
        f"Cuenta: {cuenta.numero_cuenta}"
    )

    pdf.drawString(
        11.2 * cm,
        y - 1.6 * cm,
        f"Tipo: {cuenta.get_tipo_cuenta_display()}"
    )

    pdf.drawString(
        2.5 * cm,
        y - 2.2 * cm,
        f"Saldo actual: S/ {cuenta.saldo:,.2f}"
    )

    pdf.drawString(
        11.2 * cm,
        y - 2.2 * cm,
        f"Estado: {cuenta.get_estado_display()}"
    )

    # Tabla de movimientos
    y = ALTO - 10.5 * cm
    y = dibujar_encabezado_tabla(y)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 8)

    # ==========================================
    # MOVIMIENTOS
    # ==========================================

    for movimiento in movimientos:

        # Comprobar el espacio ANTES de dibujar la fila.
        if y - alto_fila < 2.3 * cm:

            dibujar_pie_pagina(numero_pagina)
            pdf.showPage()

            numero_pagina += 1

            # En las páginas siguientes se repiten
            # la cabecera general y las columnas.
            dibujar_encabezado()

            y = ALTO - 5.2 * cm
            y = dibujar_encabezado_tabla(y)

            pdf.setFillColor(colors.black)
            pdf.setFont("Helvetica", 8)

        pdf.setStrokeColor(colors.lightgrey)

        pdf.rect(
            x1,
            y,
            x6 - x1,
            alto_fila,
            stroke=1,
            fill=0
        )

        for x in (x2, x3, x4, x5):
            pdf.line(
                x,
                y,
                x,
                y + alto_fila
            )

        # Fecha
        pdf.drawCentredString(
            (x1 + x2) / 2,
            y + 0.28 * cm,
            movimiento.fecha.strftime("%d/%m/%Y")
        )

        # Tipo
        tipo = movimiento.get_tipo_display()

        if tipo == "Transferencia":
            tipo = "Transfer."

        pdf.drawCentredString(
            (x2 + x3) / 2,
            y + 0.28 * cm,
            tipo[:18]
        )

        # Descripción
        descripcion = movimiento.descripcion or ""

        for prefijo in ("Transferencia ", "Depósito ", "Retiro "):
            if descripcion.startswith(prefijo):
                descripcion = descripcion[len(prefijo):]
                break

        pdf.drawString(
            x3 + 3,
            y + 0.28 * cm,
            descripcion[:45]
        )

        # Monto
        pdf.drawRightString(
            x5 - 3,
            y + 0.28 * cm,
            f"{movimiento.monto:,.2f}"
        )

        # Saldo
        pdf.drawRightString(
            x6 - 3,
            y + 0.28 * cm,
            f"{movimiento.saldo_actual:,.2f}"
        )

        y -= alto_fila

    # ==========================================
    # RESUMEN DEL PERÍODO
    # ==========================================

    alto_resumen = 3.5 * cm

    # Reservar espacio para el resumen y el pie.
    if y - 1.0 * cm - alto_resumen < 2.3 * cm:

        dibujar_pie_pagina(numero_pagina)
        pdf.showPage()

        numero_pagina += 1

        dibujar_encabezado()

        y = ALTO - 6.0 * cm

    else:
        y -= 1.0 * cm

    resumen_x = margen_izquierdo
    resumen_ancho = 8.5 * cm

    pdf.setStrokeColor(azul)

    pdf.roundRect(
        resumen_x,
        y - alto_resumen,
        resumen_ancho,
        alto_resumen,
        5,
        stroke=1,
        fill=0
    )

    pdf.setFillColor(azul)
    pdf.roundRect(
        resumen_x,
        y - 0.6 * cm,
        resumen_ancho,
        0.6 * cm,
        5,
        stroke=0,
        fill=1
    )

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawCentredString(
        resumen_x + resumen_ancho / 2,
        y - 0.42 * cm,
        "RESUMEN DEL PERÍODO"
    )

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    yy = y - 1.1 * cm

    # Total de depósitos
    pdf.drawString(
        resumen_x + 0.5 * cm,
        yy,
        "Total depósitos"
    )

    pdf.drawRightString(
        resumen_x + resumen_ancho - 0.5 * cm,
        yy,
        f"S/ {total_depositos:,.2f}"
    )

    yy -= 0.48 * cm

    # Total de retiros
    pdf.drawString(
        resumen_x + 0.5 * cm,
        yy,
        "Total retiros"
    )

    pdf.drawRightString(
        resumen_x + resumen_ancho - 0.5 * cm,
        yy,
        f"S/ {total_retiros:,.2f}"
    )

    yy -= 0.48 * cm

    # Transferencias recibidas
    pdf.drawString(
        resumen_x + 0.5 * cm,
        yy,
        "Transferencias recibidas"
    )

    pdf.drawRightString(
        resumen_x + resumen_ancho - 0.5 * cm,
        yy,
        f"S/ {transferencias_recibidas:,.2f}"
    )

    yy -= 0.48 * cm

    # Transferencias enviadas
    pdf.drawString(
        resumen_x + 0.5 * cm,
        yy,
        "Transferencias enviadas"
    )

    pdf.drawRightString(
        resumen_x + resumen_ancho - 0.5 * cm,
        yy,
        f"S/ {transferencias_enviadas:,.2f}"
    )

    # ==========================================
    # FINALIZAR PDF
    # ==========================================

    dibujar_pie_pagina(numero_pagina)

    pdf.save()

    return response
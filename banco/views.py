from django.shortcuts import render
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
    
def estado_cuenta(request):

    cuentas = Cuenta.objects.all()

    return render(
        request,
        "estado_cuenta.html",
        {
            "cuentas": cuentas
        }
    )
    
def estado_cuenta_pdf(request, cuenta_id):

    cuenta = Cuenta.objects.get(id=cuenta_id)
    movimientos = Movimiento.objects.filter(cuenta=cuenta)

    # Ruta del logotipo
    logo = os.path.join(
        settings.BASE_DIR,
        "static",
        "img",
        "logo_banco.png"
    )

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        f'attachment; filename="estado_cuenta_{cuenta.numero_cuenta}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)

    ANCHO, ALTO = A4

    # ============================
    # CABECERA
    # ============================
    y = ALTO - 2 * cm
    # Barra superior azul
    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.rect(
        0,
        ALTO - 0.5 * cm,
        ANCHO,
        0.5 * cm,
        fill=1,
        stroke=0
    )

    # Logotipo (si existe)

    try:
        pdf.drawImage(
            logo,
            1.8 * cm,
            ALTO - 3.0 * cm,
            width=2 * cm,
            height=2 * cm,
            preserveAspectRatio=True,
            mask='auto'
        )
    except:
        pass

    # Nombre del banco

    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.setFont("Helvetica-Bold", 22)

    pdf.drawString(
        5 * cm,
        ALTO - 1.8 * cm,
        "BANCO PYTHON"
    )

    # Lema

    pdf.setFillColor(colors.grey)

    pdf.setFont("Helvetica", 11)

    pdf.drawString(
        5 * cm,
        ALTO - 2.5 * cm,
        "Tecnología • Seguridad • Confianza"
    )

    # Fecha de emisión

    pdf.setFillColor(colors.black)

    pdf.setFont("Helvetica", 9)

    pdf.drawRightString(
        19 * cm,
        ALTO - 1.7 * cm,
        f"Emitido: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    # Línea separadora

    pdf.setStrokeColor(colors.HexColor("#0B3A75"))

    pdf.setLineWidth(1)

    pdf.line(
        2 * cm,
        ALTO - 3.6 * cm,
        19 * cm,
        ALTO - 3.6 * cm
    )

    # Título principal

    pdf.setFont("Helvetica-Bold", 18)

    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.drawCentredString(
        ANCHO / 2,
        ALTO - 4.4 * cm,
        "ESTADO DE CUENTA BANCARIO"
    )

    # =====================================================
    # DATOS DEL CLIENTE
    # =====================================================

    y = ALTO - 6.2 * cm

    # Recuadro
    pdf.setStrokeColor(colors.HexColor("#0B3A75"))
    pdf.setFillColor(colors.white)

    pdf.roundRect(
        2 * cm,
        y - 2.8 * cm,
        17 * cm,
        2.8 * cm,
        8,
        fill=1,
        stroke=1
    )

    # Título del recuadro
    pdf.setFillColor(colors.HexColor("#0B3A75"))
    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(
        2.3 * cm,
        y - 0.4 * cm,
        "DATOS DEL CLIENTE"
    )

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 10)

    # Primera línea
    pdf.drawString(
        2.5 * cm,
        y - 1.0 * cm,
        f"Cliente : {cuenta.cliente}"
    )

    # Segunda línea
    pdf.drawString(
        2.5 * cm,
        y - 1.6 * cm,
        f"Cuenta : {cuenta.numero_cuenta}"
    )

    pdf.drawString(
        11.2 * cm,
        y - 1.6 * cm,
        f"Tipo : {cuenta.get_tipo_cuenta_display()}"
    )

    # Tercera línea
    pdf.drawString(
        2.5 * cm,
        y - 2.2 * cm,
        f"Saldo actual : S/ {cuenta.saldo:,.2f}"
    )

    pdf.drawString(
        11.2 * cm,
        y - 2.2 * cm,
        f"Estado : {cuenta.get_estado_display()}"
    )

    # Posición inicial de la tabla
    y = y - 3.4 * cm
    
    # ======================================================
    # TABLA DE MOVIMIENTOS
    # ======================================================

    y -= 1 * cm  # 5.2

    alto_fila = 1.0 * cm

    # Columnas de la tabla
    x1 = 2.0 * cm      # Inicio tabla
    x2 = 4.8 * cm      # Fecha
    x3 = 7.5 * cm      # Tipo
    x4 = 13.8 * cm     # Descripción
    x5 = 16.5 * cm     # Monto
    x6 = 19.5 * cm     # Saldo

    alto_fila = 0.80 * cm

    # ============================
    # ENCABEZADO TABLA
    # ============================

    y -= 0.6 * cm
    
    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.rect(
        x1,
        y,
        x6 - x1,
        alto_fila,
        fill=1,
        stroke=1
    )

    pdf.setFillColor(colors.white)

    pdf.setFont("Helvetica-Bold", 9)

    pdf.drawCentredString((x1+x2)/2, y+0.28*cm, "Fecha")
    pdf.drawCentredString((x2+x3)/2, y+0.28*cm, "Tipo")
    pdf.drawCentredString((x3+x4)/2, y+0.28*cm, "Descripción")
    pdf.drawCentredString((x4+x5)/2, y+0.28*cm, "Monto")
    pdf.drawCentredString((x5+x6)/2, y+0.28*cm, "Saldo")  
    
    y -= 0.25 * cm

    pdf.line(
        2 * cm,
        y,
        19 * cm,
        y
    )

    y -= 0.5 * cm

    pdf.setFont("Helvetica", 9)
    
    y -= alto_fila

    # ============================
    # MOVIMIENTOS
    # ============================

    print("TOTAL MOVIMIENTOS:", movimientos.count())
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 12)

    for movimiento in movimientos:

        pdf.rect(x1, y, x6-x1, alto_fila, stroke=1, fill=0)

        pdf.line(x2, y, x2, y+alto_fila)
        pdf.line(x3, y, x3, y+alto_fila)
        pdf.line(x4, y, x4, y+alto_fila)
        pdf.line(x5, y, x5, y+alto_fila)

        pdf.drawString(
            x1 + 2,
            y + 0.28 * cm,
            movimiento.fecha.strftime("%d/%m/%Y")
        )

        tipo = movimiento.get_tipo_display()

        if tipo == "Transferencia":
            tipo = "Transfer."

        pdf.drawString(
            x2 + 2,
            y + 0.28 * cm,
            tipo
        )
        
        # ==========================
        # LIMPIAR LA DESCRIPCIÓN
        # ==========================

        descripcion = movimiento.descripcion

        if descripcion.startswith("Transferencia"):
            descripcion = descripcion.replace("Transferencia ", "", 1)

        if descripcion.startswith("Depósito"):
            descripcion = descripcion.replace("Depósito ", "", 1)

        if descripcion.startswith("Retiro"):
            descripcion = descripcion.replace("Retiro ", "", 1)

        pdf.drawString(
            x3 + 2,
            y + 0.28 * cm,
            descripcion[:28]
        )

        # ==========================
        # MONTO
        # ==========================

        pdf.drawRightString(
            x5 - 3,
            y + 0.28 * cm,
            f"S/ {movimiento.monto:,.2f}"
        )

        # ==========================
        # SALDO
        # ==========================

        pdf.drawRightString(
            x6 - 3,
            y + 0.28 * cm,
            f"S/ {movimiento.saldo_actual:,.2f}"
        )

        # Pasar a la siguiente fila
        y -= alto_fila

        # Nueva página si ya no hay espacio
        if y < 3 * cm:
            pdf.showPage()
            y = ALTO - 2 * cm

        # ==========================
        # LIMPIAR LA DESCRIPCIÓN
        # ==========================

                    
    total_depositos = sum(m.monto for m in movimientos if m.tipo == "D")
    total_retiros = sum(m.monto for m in movimientos if m.tipo == "R")
    total_transferencias = sum(m.monto for m in movimientos if m.tipo == "T"
    )

    # ======================================
    # RESUMEN DEL PERÍODO
    # ======================================

    y -= 1 * cm

    alto_resumen = 3.2 * cm

    pdf.setStrokeColor(colors.HexColor("#0B3A75"))

    pdf.roundRect(
        2 * cm,
        y - alto_resumen,
        8.5 * cm,
        alto_resumen,
        5,
        stroke=1,
        fill=0
    )

    # Título
    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(colors.HexColor("#0B3A75"))

    pdf.rect(
        5.5 * cm,
        y - 0.6 * cm,
        8 * cm,
        0.5 * cm,
        fill=1,
        stroke=0
    )

    pdf.setFillColor(colors.white)

    pdf.setFont("Helvetica-Bold",9)

    pdf.drawCentredString(
        9.5 * cm,
        y - 0.43 * cm,
        "RESUMEN DEL PERÍODO"
    )

    # Contenido
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)

    yy = y - 1.1 * cm

    pdf.drawString(2.5 * cm, yy, "Total depósitos")
    pdf.drawRightString(10 * cm, yy, f"S/ {total_depositos:,.2f}")

    yy -= 0.55 * cm

    pdf.drawString(2.5 * cm, yy, "Total retiros")
    pdf.drawRightString(10 * cm, yy, f"S/ {total_retiros:,.2f}")

    yy -= 0.55 * cm

    pdf.drawString(2.5 * cm, yy, "Total transferencias")
    pdf.drawRightString(10 * cm, yy, f"S/ {total_transferencias:,.2f}")
        
    pdf.line(
        2 * cm,
        y,
        19 * cm,
        y
    )           
    
    # ============================
    # PIE DE PÁGINA
    # ============================

    pdf.setStrokeColor(colors.HexColor("#0B3A75"))
    pdf.setLineWidth(0.8)

    pdf.line(
        2 * cm,
        1.8 * cm,
        19 * cm,
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
        19 * cm,
        1.3 * cm,
        "Página 1"
    )   
    
    pdf.save()
    return response


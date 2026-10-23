from django.shortcuts import render
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from django.db.models import Sum, Avg, Max, Min
from clientes.models import Cliente
from cuentas.models import Cuenta
from movimientos.models import Movimiento
from datetime import datetime
from openpyxl import Workbook
from .utils import encabezado_reporte, pie_pagina
from openpyxl.styles import Border, Side, PatternFill, Alignment, Font
from usuarios.decorators import grupos_permitidos
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from copy import copy
from decimal import Decimal


@grupos_permitidos("Administrador", "Supervisor")
def index(request):
    return render(request, "reportes/index.html")

@grupos_permitidos("Administrador", "Supervisor")
def reporte_dashboard_pdf(request):

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        'attachment; filename="Dashboard_Bancario.pdf"'
    )

    doc = SimpleDocTemplate(response)

    elementos = encabezado_reporte("REPORTE EJECUTIVO DEL BANCO")

    estilos = getSampleStyleSheet()

    elementos.append(

        Paragraph(

            "<b>Últimos movimientos</b>",

            estilos["Heading2"]

        )

    )

    movimientos = (

        Movimiento.objects
        .select_related("cuenta")
        .order_by("-fecha")[:5]

    )

    datos_mov = [

        ["Cuenta", "Tipo", "Monto", "Fecha"]

    ]

    for mov in movimientos:

        datos_mov.append([

            mov.cuenta.numero_cuenta,

            mov.get_tipo_display(),

            f"S/. {mov.monto:,.2f}",

            mov.fecha.strftime("%d/%m/%Y")

        ])

    tabla2 = Table(datos_mov)

    tabla2.setStyle(

        TableStyle([

            ("BACKGROUND",(0,0),(-1,0),colors.darkgreen),

            ("TEXTCOLOR",(0,0),(-1,0),colors.white),

            ("GRID",(0,0),(-1,-1),1,colors.grey),

            ("BACKGROUND",(0,1),(-1,-1),colors.whitesmoke),

            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

        ])

    )

    elementos.append(tabla2)

    elementos.append(Spacer(1, 20))

    total_clientes = Cliente.objects.count()
    total_cuentas = Cuenta.objects.count()

    saldo_total = (
        Cuenta.objects.aggregate(total=Sum("saldo"))["total"] or 0
    )

    saldo_promedio = (
        Cuenta.objects.aggregate(promedio=Avg("saldo"))["promedio"] or 0
    )

    mayor_saldo = (
        Cuenta.objects.aggregate(maximo=Max("saldo"))["maximo"] or 0
    )

    menor_saldo = (
        Cuenta.objects.aggregate(minimo=Min("saldo"))["minimo"] or 0
    )

    datos = [

        ["Indicador", "Valor"],

        ["Clientes", total_clientes],

        ["Cuentas", total_cuentas],

        ["Saldo total", f"S/. {saldo_total:,.2f}"],

        ["Saldo promedio", f"S/. {saldo_promedio:,.2f}"],

        ["Mayor saldo", f"S/. {mayor_saldo:,.2f}"],

        ["Menor saldo", f"S/. {menor_saldo:,.2f}"],

    ]

    tabla = Table(datos)

    tabla.setStyle(

        TableStyle([

            ("BACKGROUND", (0,0), (-1,0), colors.darkblue),

            ("TEXTCOLOR", (0,0), (-1,0), colors.white),

            ("GRID", (0,0), (-1,-1), 1, colors.grey),

            ("BACKGROUND", (0,1), (-1,-1), colors.beige),

            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

            ("BOTTOMPADDING", (0,0), (-1,0), 10),

        ])

    )

    tabla = Table(datos)

    elementos.append(tabla)

    doc.build(
        elementos,
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina
    )

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_dashboard_excel(request):

    wb = Workbook()
    ws = wb.active
    ws.title = "Dashboard"

    ws["A1"] = "REPORTE EJECUTIVO DEL BANCO"

    ws.append([])

    ws.append(["Indicador", "Valor"])

    total_clientes = Cliente.objects.count()
    total_cuentas = Cuenta.objects.count()

    saldo_total = Cuenta.objects.aggregate(
        total=Sum("saldo")
    )["total"] or 0

    saldo_promedio = Cuenta.objects.aggregate(
        promedio=Avg("saldo")
    )["promedio"] or 0

    mayor_saldo = Cuenta.objects.aggregate(
        maximo=Max("saldo")
    )["maximo"] or 0

    menor_saldo = Cuenta.objects.aggregate(
        minimo=Min("saldo")
    )["minimo"] or 0

    ws.append(["Clientes", total_clientes])
    ws.append(["Cuentas", total_cuentas])
    ws.append(["Saldo total", float(saldo_total)])
    ws.append(["Saldo promedio", float(saldo_promedio)])
    ws.append(["Mayor saldo", float(mayor_saldo)])
    ws.append(["Menor saldo", float(menor_saldo)])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    response["Content-Disposition"] = (
        'attachment; filename="Dashboard_Bancario.xlsx"'
    )

    wb.save(response)

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_clientes_pdf(request):

    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        'attachment; filename="Clientes.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
    )

    elementos = encabezado_reporte("REPORTE DE CLIENTES")

    datos = [
        ["DNI", "Nombre", "Teléfono", "Correo"]
    ]

    clientes = Cliente.objects.all().order_by(
        "apellidos", "nombres"
    )

    total_clientes = clientes.count()

    for cliente in clientes:
        datos.append([
            cliente.dni,
            f"{cliente.apellidos}, {cliente.nombres}",
            cliente.telefono,
            cliente.correo,
        ])

    # Crear la tabla una sola vez
    tabla = Table(
        datos,
        repeatRows=1,
        colWidths=[75, 155, 90, 150]
    )

    # Aplicar los estilos a la misma tabla
    tabla.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#EAF1F8")]
            ),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    elementos.append(tabla)

    total_clientes = Cliente.objects.count()

    estilos = getSampleStyleSheet()

    elementos.append(
        Paragraph(
            f"<b>Total de clientes:</b> {total_clientes}",
            estilos["Normal"]
        )
    )

    elementos.append(Spacer(1, 5))

    doc.build(
        elementos,
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina
    )

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_clientes_excel(request):

    wb = Workbook()

    ws = wb.active
    ws.title = "Clientes"

    # ============================
    # TÍTULO DEL REPORTE
    # ============================

    ws.merge_cells("A1:J1")
    ws["A1"] = "BANCO PYTHON - REPORTE DE CLIENTES"
    ws["A1"].font = Font(
        name="Arial",
        size=16,
        bold=True,
        color="FFFFFF"
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

    # FECHA DE EMISIÓN

    ws.merge_cells("A2:J2")
    ws["A2"] = (
        "Fecha de emisión: "
        + datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    ws["A2"].font = Font(
        name="Arial",
        size=10,
        italic=True
    )
    ws["A2"].alignment = Alignment(
        horizontal="right"
    )
    ws.row_dimensions[2].height = 22

    # ENCABEZADOS DE LA TABLA

    ws.append([
        "N.º",
        "DNI",
        "Nombres",
        "Apellidos",
        "Fecha de nacimiento",
        "Dirección",
        "Teléfono",
        "Correo",
        "Estado",
        "Fecha de registro",
    ])

    # ============================
    # CLIENTES
    # ============================

    clientes = Cliente.objects.all().order_by(
        "apellidos",
        "nombres"
    )

    for numero, cliente in enumerate(clientes, start=1):

        ws.append([

            numero,

            cliente.dni,

            cliente.nombres,

            cliente.apellidos,

            cliente.fecha_nacimiento.strftime("%d/%m/%Y")
            if cliente.fecha_nacimiento else "",

            cliente.direccion,

            cliente.telefono,

            cliente.correo,

            cliente.get_estado_display(),

            cliente.fecha_registro.strftime("%d/%m/%Y %H:%M")
            if cliente.fecha_registro else "",

        ])

    # ============================
    # RESUMEN DE CLIENTES
    # ============================

    total_clientes = clientes.count()

    total_activos = clientes.filter(estado="A").count()

    total_inactivos = clientes.filter(estado="I").count()

    # Dejar una fila en blanco
    ws.append([])

    # Primera fila del resumen
    fila_total = ws.max_row + 1

    resumen = [
        ("Total de clientes:", total_clientes),
        ("Clientes activos:", total_activos),
        ("Clientes inactivos:", total_inactivos),
    ]

    for i, (etiqueta, valor) in enumerate(resumen):
        fila = fila_total + i

        ws.cell(row=fila, column=1, value=etiqueta)
        ws.cell(row=fila, column=2, value=valor)

        # Estilo de la etiqueta
        celda_etiqueta = ws.cell(row=fila, column=1)
        celda_etiqueta.font = Font(bold=True)
        celda_etiqueta.fill = PatternFill(
            fill_type="solid",
            fgColor="EAF1F8"
        )
        celda_etiqueta.alignment = Alignment(
            horizontal="left",
            vertical="center"
        )

        # Estilo del valor
        celda_valor = ws.cell(row=fila, column=2)
        celda_valor.font = Font(bold=True)
        celda_valor.fill = PatternFill(
            fill_type="solid",
            fgColor="EAF1F8"
        )
        celda_valor.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # Aplicar fondo a toda la fila del resumen
    for fila in range(fila_total, fila_total + 3):
        for columna in range(1, 11):
            ws.cell(row=fila, column=columna).fill = PatternFill(
                fill_type="solid",
                fgColor="EAF1F8"
            )

    # ============================
    # ESTILO DEL ENCABEZADO
    # ============================

    for celda in ws[3]:

        fuente = copy(celda.font)
        fuente.bold = True
        fuente.color = "FFFFFF"
        celda.font = fuente

        celda.fill = PatternFill(
            fill_type="solid",
            fgColor="0B3A75"
        )

        celda.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    # ============================
    # ANCHO DE COLUMNAS
    # ============================

    anchos = {
        "A": 23,
        "B": 12,
        "C": 25,
        "D": 30,
        "E": 22,
        "F": 40,
        "G": 18,
        "H": 35,
        "I": 15,
        "J": 22,
    }

    for columna, ancho in anchos.items():

        ws.column_dimensions[columna].width = ancho

    # ============================
    # TAMAÑO DE LETRA Y ALTURA
    # ============================

    for fila in range(1, ws.max_row + 1):
        ws.row_dimensions[fila].height = 18

    # Encabezados de la tabla
    for celda in ws[3]:
        celda.font = Font(
            name="Arial",
            size=10,
            bold=True,
            color="FFFFFF"
        )

    # Datos de los clientes
    for fila in range(4, total_clientes + 4):
        for celda in ws[fila]:
            celda.font = Font(
                name="Arial",
                size=9
            )

    # Resumen de clientes
    for fila in range(total_clientes + 5, ws.max_row + 1):
        for celda in ws[fila]:
            celda.font = Font(
                name="Arial",
                size=9,
                bold=True
            )

    # ============================
    # ALINEACIÓN DE DATOS
    # ============================

    for fila in range(4, total_clientes + 4):
        for celda in ws[fila]:
            celda.alignment = Alignment(
                vertical="center"
            )

    # Centrar columnas numéricas, fechas y estado
    for fila in range(4, total_clientes + 4):
        for columna in ("A", "B", "E", "G", "I", "J"):
            ws[f"{columna}{fila}"].alignment = Alignment(
                horizontal="center",
                vertical="center"
            )

    # ============================
    # FILTRO
    # ============================

    total_clientes = clientes.count()

    ws.auto_filter.ref = f"A1:J{total_clientes + 1}"

    # ============================
    # CONGELAR TÍTULO Y ENCABEZADOS
    # ============================

    ws.freeze_panes = "A4"

    # ============================
    # CONFIGURACIÓN DE IMPRESIÓN
    # ============================

    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4

    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False

    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.40
    ws.page_margins.bottom = 0.40

    ws.print_area = f"A1:J{ws.max_row}"

    # ============================
    # RESPUESTA
    # ============================

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="Clientes.xlsx"'
    )

    wb.save(response)

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_cuentas_pdf(request):

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="Cuentas.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
    )

    elementos = encabezado_reporte("REPORTE DE CUENTAS")

    estilos = getSampleStyleSheet()

    datos = [[
        "N.º Cuenta",
        "Cliente",
        "Tipo",
        "Saldo",
    ]]

    cuentas = (
        Cuenta.objects
        .select_related("cliente")
        .order_by("numero_cuenta")
    )

    for cuenta in cuentas:
        datos.append([
            cuenta.numero_cuenta,
            f"{cuenta.cliente.apellidos}, "
            f"{cuenta.cliente.nombres}",
            cuenta.get_tipo_cuenta_display(),
            f"S/. {cuenta.saldo:,.2f}",
        ])

    tabla = Table(
        datos,
        repeatRows=1,
        colWidths=[90, 230, 100, 85],
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3A75")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#EAF2F8")],
        ),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 12))

    total_cuentas = cuentas.count()

    saldo_total = (
        cuentas.aggregate(total=Sum("saldo"))["total"] or 0
    )

    elementos.append(
        Paragraph(
            f"<b>Total de cuentas registradas:</b> {total_cuentas}",
            estilos["Normal"],
        )
    )

    elementos.append(Spacer(1, 6))

    elementos.append(
        Paragraph(
            f"<b>Saldo total:</b> S/. {saldo_total:,.2f}",
            estilos["Normal"],
        )
    )

    doc.build(
        elementos,
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina,
    )

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_movimientos_pdf(request):

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="Movimientos.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.5 * cm,
    )

    elementos = []

    # ============================
    # ENCABEZADO
    # ============================

    elementos.extend(
        encabezado_reporte("REPORTE DE MOVIMIENTOS BANCARIOS")
    )

    estilos = getSampleStyleSheet()

    # ============================
    # CONSULTA DE MOVIMIENTOS
    # ============================

    movimientos = (
        Movimiento.objects
        .select_related("cuenta", "cuenta__cliente")
        .order_by("-fecha")
    )

    # ============================
    # DATOS DE LA TABLA
    # ============================

    datos = [[
        "Cuenta",
        "Cliente",
        "Tipo",
        "Monto",
        "Saldo actual",
        "Fecha",
    ]]

    for movimiento in movimientos:
        cuenta = movimiento.cuenta
        cliente = cuenta.cliente

        datos.append([
            Paragraph(
                str(cuenta.numero_cuenta),
                estilos["Normal"]
            ),
            Paragraph(
                f"{cliente.apellidos}, {cliente.nombres}",
                estilos["Normal"]
            ),
            Paragraph(
                movimiento.get_tipo_display(),
                estilos["Normal"]
            ),
            Paragraph(
                f"S/. {movimiento.monto:,.2f}",
                estilos["Normal"]
            ),
            Paragraph(
                f"S/. {movimiento.saldo_actual:,.2f}",
                estilos["Normal"]
            ),
            Paragraph(
                movimiento.fecha.strftime("%d/%m/%Y %H:%M")
                if movimiento.fecha else "",
                estilos["Normal"]
            ),
        ])

    # ============================
    # TABLA
    # ============================

    tabla = Table(
        datos,
        repeatRows=1,
        colWidths=[65, 130, 75, 65, 75, 85],
        hAlign="LEFT",
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3A75")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#EAF2F8")],
        ),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("ALIGN", (5, 1), (5, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(tabla)
    elementos.append(Spacer(1, 3))

    # ============================
    # RESUMEN FINANCIERO
    # ============================

    total_movimientos = movimientos.count()

    total_montos = (
        movimientos.aggregate(total=Sum("monto"))["total"] or 0
    )

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

    estilos = getSampleStyleSheet()

    # ============================
    # ESTILO PARA EL TIPO DE MOVIMIENTO
    # ============================

    estilo_tipo = ParagraphStyle(
        "TipoMovimiento",
        parent=estilos["Normal"],
        fontSize=8,
        leading=10,
    )

    elementos.append(Spacer(1, 10))

    resumen = [
        ["Concepto", "Cantidad / Importe"],
        ["Total de movimientos", str(total_movimientos)],
        ["Suma de montos", f"S/. {total_montos:,.2f}"],
        ["Total de depósitos", f"S/. {total_depositos:,.2f}"],
        ["Total de retiros", f"S/. {total_retiros:,.2f}"],
        ["Total de transferencias", f"S/. {total_transferencias:,.2f}"],
    ]

    tabla_resumen = Table(
        resumen,
        colWidths=[250, 150],
        repeatRows=1
    )

    tabla_resumen.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B3A75")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("FONTSIZE", (0, 1), (-1, -1), 11),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#EAF2F8")]
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )

    # ============================
    # RESUMEN FINANCIERO SIN DIVIDIR
    # ============================

    estilo_titulo_resumen = ParagraphStyle(
        "TituloResumen",
        parent=estilos["Heading2"],
        fontSize=14,
        leading=17,
        spaceAfter=4,
    )

    titulo_resumen = Paragraph(
        "<b>RESUMEN FINANCIERO</b>",
        estilo_titulo_resumen
    )

    elementos.append(
        KeepTogether([
            titulo_resumen,
            Spacer(1, 2),
            tabla_resumen,
        ])
    )

    # ============================
    # GENERAR PDF
    # ============================

    doc.build(
        elementos,
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina,
    )

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_movimientos_excel(request):

    wb = Workbook()

    ws = wb.active
    ws.title = "Movimientos"

    # ============================
    # TÍTULO DEL REPORTE
    # ============================

    from datetime import datetime

    ws.merge_cells("A1:H1")
    ws["A1"] = "BANCO PYTHON - REPORTE DE MOVIMIENTOS"
    ws["A1"].font = Font(
        name="Arial",
        size=16,
        bold=True,
        color="FFFFFF"
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

    # FECHA DE EMISIÓN

    ws.merge_cells("A2:H2")
    ws["A2"] = (
        "Fecha de emisión: "
        + datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    ws["A2"].font = Font(
        name="Arial",
        size=10,
        italic=True
    )
    ws["A2"].alignment = Alignment(
        horizontal="right"
    )
    ws.row_dimensions[2].height = 22

    # ENCABEZADOS DE LA TABLA

    ws.append([
        "Fecha",
        "Cuenta",
        "Cliente",
        "Tipo",
        "Monto",
        "Saldo anterior",
        "Saldo actual",
        "Descripción",
    ])

    # DATOS
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    tipo = request.GET.get("tipo")


    movimientos = (
        Movimiento.objects
        .select_related("cuenta", "cuenta__cliente")
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

    for movimiento in movimientos:
        cliente = movimiento.cuenta.cliente

        ws.append([
            movimiento.fecha.strftime("%d/%m/%Y %H:%M"),
            movimiento.cuenta.numero_cuenta,
            f"{cliente.apellidos}, {cliente.nombres}",
            movimiento.get_tipo_display(),
            float(movimiento.monto),
            float(movimiento.saldo_anterior),
            float(movimiento.saldo_actual),
            movimiento.descripcion,
        ])

    # Guardar la última fila que contiene movimientos
    ultima_fila_datos = ws.max_row

    # Última fila que contiene movimientos, sin incluir el resumen
    ultima_fila_datos = ws.max_row

    # EL RESUMEN VA FUERA DEL BUCLE FOR

    total_movimientos = movimientos.count()

    total_depositos = (
        movimientos.filter(tipo="D")
        .aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    )

    total_retiros = (
        movimientos.filter(tipo="R")
        .aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    )

    total_transferencias = (
        movimientos.filter(tipo="T")
        .aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    )

    total_montos = (
        total_depositos
        + total_retiros
        + total_transferencias
    )

    ws.append([])

    ws.append([
        "Total de movimientos:",
        total_movimientos,
    ])

    ws.append([
        "Suma de montos:",
        None,
        None,
        None,
        float(total_montos),
    ])

    ws.append([
        "Total de depósitos:",
        None,
        None,
        None,
        float(total_depositos),
    ])

    ws.append([
        "Total de retiros:",
        None,
        None,
        None,
        float(total_retiros),
    ])

    ws.append([
        "Total de transferencias:",
        None,
        None,
        None,
        float(total_transferencias),
    ])

    # ============================
    # ESTILO DEL RESUMEN FINANCIERO
    # ============================

    from openpyxl.styles import Border, Side

    fila_inicio_resumen = ws.max_row - 4
    fila_fin_resumen = ws.max_row

    borde_fino = Side(
        style="thin",
        color="B7C9D6"
    )

    for fila in range(fila_inicio_resumen, fila_fin_resumen + 1):

        for columna in range(1, 9):

            celda = ws.cell(
                row=fila,
                column=columna
            )

            celda.fill = PatternFill(
                fill_type="solid",
                fgColor="EAF2F8"
            )

            celda.border = Border(
                bottom=borde_fino
            )

        # Etiquetas del resumen en negrita
        ws[f"A{fila}"].font = Font(bold=True)

        # Formato monetario en la columna E
        if fila >= fila_inicio_resumen + 1:
            ws[f"E{fila}"].number_format = '"S/." #,##0.00'
            ws[f"E{fila}"].alignment = Alignment(
                horizontal="right"
            )

    # Destacar especialmente la suma total
    ws[f"A{fila_inicio_resumen + 1}"].font = Font(
        bold=True,
        color="0B3A75"
    )

    ws[f"E{fila_inicio_resumen + 1}"].font = Font(
        bold=True,
        color="0B3A75"
    )

    # Altura de las filas del resumen
    for fila in range(fila_inicio_resumen, fila_fin_resumen + 1):
        ws.row_dimensions[fila].height = 22

    # ESTILO DEL ENCABEZADO

    for celda in ws[3]:

        celda.font = celda.font.copy(
            bold=True,
            color="FFFFFF"
        )

        celda.fill = PatternFill(
            fill_type="solid",
            fgColor="0B3A75"
        )

        celda.alignment = Alignment(
            horizontal="center"
        )

    # ANCHO DE COLUMNAS

    anchos = {
        "A": 20,
        "B": 18,
        "C": 35,
        "D": 20,
        "E": 15,
        "F": 18,
        "G": 18,
        "H": 40,
    }

    for columna, ancho in anchos.items():

        ws.column_dimensions[columna].width = ancho

    # FORMATO MONETARIO DE LOS MOVIMIENTOS

    for fila in range(4, ultima_fila_datos + 1):
        ws[f"A{fila}"].number_format = "dd/mm/yyyy hh:mm"

        for columna in ("E", "F", "G"):

            ws[f"{columna}{fila}"].number_format = (
                '"S/." #,##0.00'
            )

    # FILTRO

    ws.auto_filter.ref = f"A3:H{ultima_fila_datos}"

    # CONGELAR ENCABEZADO

    ws.freeze_panes = "A4"

    # ============================
    # CONFIGURACIÓN DE IMPRESIÓN
    # ============================

    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    ws.page_margins.left = 0.20
    ws.page_margins.right = 0.20
    ws.page_margins.top = 0.35
    ws.page_margins.bottom = 0.35

    ws.page_margins.header = 0.15
    ws.page_margins.footer = 0.15

    # Repetir encabezados de la tabla
    ws.print_title_rows = "3:3"

    # Área de impresión completa
    ws.print_area = f"A1:H{ws.max_row}"

    # RESPUESTA

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="Movimientos.xlsx"'
    )

    wb.save(response)

    return response

@grupos_permitidos("Administrador", "Supervisor")
def reporte_cuentas_excel(request):

    wb = Workbook()

    ws = wb.active
    ws.title = "Cuentas"

    # ============================
    # ENCABEZADOS
    # ============================

    ws.append([
        "N.º",
        "Número de cuenta",
        "Cliente",
        "Tipo",
        "Saldo",
        "Fecha de apertura",
        "Estado",
    ])

    # ============================
    # CUENTAS
    # ============================

    cuentas = (
        Cuenta.objects
        .select_related("cliente")
        .order_by("numero_cuenta")
    )

    for numero, cuenta in enumerate(cuentas, start=1):

        ws.append([

            numero,

            cuenta.numero_cuenta,

            f"{cuenta.cliente.apellidos}, "
            f"{cuenta.cliente.nombres}",

            cuenta.get_tipo_cuenta_display(),

            float(cuenta.saldo),

            cuenta.fecha_apertura.strftime("%d/%m/%Y")
            if cuenta.fecha_apertura else "",

            cuenta.get_estado_display(),

])

    # ============================
    # RESUMEN DE CUENTAS
    # ============================

    from decimal import Decimal

    total_cuentas = cuentas.count()

    total_activas = cuentas.filter(estado="A").count()
    total_inactivas = cuentas.filter(estado="I").count()

    saldo_total = sum(
        (cuenta.saldo for cuenta in cuentas),
        Decimal("0.00")
    )

    ws.append([])  # Dejar una fila en blanco antes del resumen

    resumen = [
        ("Total de cuentas:", total_cuentas, None),
        ("Cuentas activas:", total_activas, None),
        ("Cuentas inactivas:", total_inactivas, None),
        ("Saldo total:", None, float(saldo_total)),
    ]

    for etiqueta, cantidad, saldo in resumen:
        fila = ws.max_row + 1

        ws.cell(row=fila, column=1, value=etiqueta)

        if cantidad is not None:
            ws.cell(row=fila, column=2, value=cantidad)

        if saldo is not None:
            ws.cell(row=fila, column=5, value=saldo)
            ws.cell(row=fila, column=5).number_format = '"S/." #,##0.00'

        for columna in range(1, 8):
            celda = ws.cell(row=fila, column=columna)
            celda.fill = PatternFill(
                fill_type="solid",
                fgColor="EAF2F8"
            )

        ws.cell(row=fila, column=1).font = Font(bold=True)
        ws.cell(row=fila, column=2).font = Font(bold=True)
        ws.cell(row=fila, column=5).font = Font(bold=True)

    # ESTILO DEL ENCABEZADO

    for celda in ws[1]:

        fuente = copy(celda.font)
        fuente.bold = True
        fuente.color = "FFFFFF"
        celda.font = fuente

        celda.fill = PatternFill(
            fill_type="solid",
            fgColor="0B3A75"
        )

        celda.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    ws.row_dimensions[1].height = 25

    # ============================
    # ANCHO DE COLUMNAS
    # ============================

    anchos = {
    "A": 24,
    "B": 23,
    "C": 35,
    "D": 22,
    "E": 20,
    "F": 23,
    "G": 16,
}

    for columna, ancho in anchos.items():

        ws.column_dimensions[columna].width = ancho

    # ============================
    # FORMATO MONETARIO
    # ============================

    for fila in range(2, total_cuentas + 2):
        ws[f"E{fila}"].number_format = '"S/." #,##0.00'

    # ============================
    # FILTRO
    # ============================

    ws.auto_filter.ref = f"A1:G{total_cuentas + 1}"

    # ============================
    # CONGELAR ENCABEZADO
    # ============================

    ws.freeze_panes = "A2"

    # ============================
    # CONFIGURACIÓN DE IMPRESIÓN
    # ============================

    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    ws.print_options.horizontalCentered = True
    ws.print_options.verticalCentered = False

    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.40
    ws.page_margins.bottom = 0.40

    ws.print_area = f"A1:G{ws.max_row}"

    # ============================
    # RESPUESTA
    # ============================

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="Cuentas.xlsx"'
    )

    wb.save(response)

    return response




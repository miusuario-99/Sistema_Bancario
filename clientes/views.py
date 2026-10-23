from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente
from .forms import ClienteForm
from django.core.paginator import Paginator
from django.db.models import Q
from openpyxl import Workbook
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from auditoria.utils import registrar_auditoria
from openpyxl.styles import PatternFill, Alignment
from usuarios.decorators import grupos_permitidos
from cuentas.models import Cuenta


# ==========================
# LISTAR CLIENTES
# ==========================
@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def lista_clientes(request):

    query = request.GET.get("q", "")

    clientes = Cliente.objects.all()

    # 🔍 BUSCADOR
    if query:
        clientes = clientes.filter(
            Q(dni__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query)
        )

    # 📄 PAGINACIÓN
    paginator = Paginator(clientes, 5)  # 5 por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ==========================
    # ESTADÍSTICAS
    # ==========================

    total_clientes = Cliente.objects.count()

    clientes_activos = Cliente.objects.filter(
        estado="A"
    ).count()

    clientes_inactivos = Cliente.objects.filter(
        estado="I"
    ).count()

    return render(request, "clientes/lista.html", {

        "page_obj": page_obj,
        "query": query,

        "total_clientes": total_clientes,
        "clientes_activos": clientes_activos,
        "clientes_inactivos": clientes_inactivos,

    })

# ==========================
# NUEVO CLIENTE
# ==========================
@grupos_permitidos("Administrador", "Cajero")
def nuevo_cliente(request):

    if request.method == "POST":

        form = ClienteForm(request.POST)

        if form.is_valid():            
            cliente = form.save()

            registrar_auditoria(
                request,
                "Clientes",
                "Nuevo cliente",
                f"Cliente: {cliente.dni} - {cliente.nombres} {cliente.apellidos}"
            )
            messages.success(request, "Cliente registrado correctamente.")
            return redirect("lista_clientes")

    else:

        form = ClienteForm()

    return render(request, "clientes/formulario.html", {
        "form": form,
        "titulo": "Nuevo Cliente"
    })


# ==========================
# EDITAR CLIENTE
# ==========================
@grupos_permitidos("Administrador")
def editar_cliente(request, id):

    cliente = get_object_or_404(Cliente, id=id)

    if request.method == "POST":

        form = ClienteForm(request.POST, instance=cliente)

        if form.is_valid():
           
            cliente = form.save()

            registrar_auditoria(
                request,
                "Clientes",
                "Editar",
                f"Cliente: {cliente.dni} - {cliente.nombres} {cliente.apellidos}"
            )
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("lista_clientes")

    else:

        form = ClienteForm(instance=cliente)

    return render(request, "clientes/formulario.html", {
        "form": form,
        "titulo": "Editar"
    })

# ==========================
# ELIMINAR CLIENTE
# ==========================
@grupos_permitidos("Administrador")
def eliminar_cliente(request, id):

    if request.method != "POST":
        messages.error(
            request,
            "La eliminación requiere una solicitud POST."
        )
        return redirect("lista_clientes")

    cliente = get_object_or_404(Cliente, id=id)

    # Proteger las cuentas bancarias y sus movimientos
    if Cuenta.objects.filter(cliente=cliente).exists():
        messages.error(
            request,
            "No se puede eliminar este cliente porque "
            "tiene cuentas bancarias asociadas. "
            "Debe conservarse su historial bancario."
        )
        return redirect("lista_clientes")

    # Guardar los datos antes de eliminar
    detalle_cliente = (
        f"Cliente: {cliente.dni} - "
        f"{cliente.nombres} {cliente.apellidos}"
    )

    # Registrar la auditoría antes de eliminar
    registrar_auditoria(
        request,
        "Clientes",
        "Eliminar",
        detalle_cliente
    )

    cliente.delete()

    messages.success(
        request,
        "Cliente eliminado correctamente."
    )

    return redirect("lista_clientes")

    # ==========================
    # EXPORTAR CLIENTES A EXCEL
    # ==========================

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def exportar_clientes_excel(request):
    # Código existente de exportación Excel
    wb = Workbook()

    ws = wb.active

    ws.title = "Clientes"

    # ============================
    # ENCABEZADOS
    # ============================

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

        estado = (
            "Activo"
            if cliente.estado == "A"
            else "Inactivo"
        )

        ws.append([

            numero,

            cliente.dni,

            cliente.nombres,

            cliente.apellidos,

            cliente.fecha_nacimiento.strftime(
                "%d/%m/%Y"
            ),

            cliente.direccion,

            cliente.telefono,

            cliente.correo,

            estado,

            cliente.fecha_registro.strftime(
                "%d/%m/%Y %H:%M"
            ),

        ])

    # ============================
    # ESTILO DEL ENCABEZADO
    # ============================

    for celda in ws[1]:

        celda.font = celda.font.copy(
            bold=True,
            color="FFFFFF"
        )

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
        "A": 8,
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
    # FILTRO
    # ============================

    ws.auto_filter.ref = ws.dimensions

    # ============================
    # CONGELAR ENCABEZADO
    # ============================

    ws.freeze_panes = "A2"

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

# ==========================
# EXPORTAR CLIENTES PDF
# ==========================

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def exportar_clientes_pdf(request):
    import os
    from datetime import datetime

    from django.conf import settings
    from django.http import HttpResponse

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        Image,
    )

    # Crear la respuesta PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="clientes.pdf"'
    )

    # Configurar documento A4 horizontal
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    elementos = []
    estilos = getSampleStyleSheet()

    # Estilos del encabezado
    estilo_titulo = ParagraphStyle(
        "TituloBanco",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#0B3A75"),
        alignment=TA_CENTER,
        spaceAfter=5,
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloReporte",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    estilo_celda = ParagraphStyle(
        "CeldaReporte",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        wordWrap="CJK",
    )

    estilo_encabezado = ParagraphStyle(
        "EncabezadoTabla",
        parent=estilo_celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    # Logo, si existe
    ruta_logo = os.path.join(
        settings.BASE_DIR,
        "static",
        "img",
        "logo_banco.png",
    )

    if os.path.exists(ruta_logo):
        logo = Image(
            ruta_logo,
            width=22 * mm,
            height=22 * mm,
            kind="proportional",
        )
        logo.hAlign = "CENTER"
        elementos.append(logo)
        elementos.append(Spacer(1, 4 * mm))

    # Títulos y fecha
    elementos.append(
        Paragraph("BANCO PYTHON", estilo_titulo)
    )

    elementos.append(
        Paragraph(
            "Sistema de Gestión Bancaria",
            estilo_subtitulo,
        )
    )

    elementos.append(
        Paragraph(
            "REPORTE GENERAL DE CLIENTES",
            estilo_subtitulo,
        )
    )

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos.append(
        Paragraph(
            f"<b>Fecha de emisión:</b> {fecha}",
            estilos["Normal"],
        )
    )

    elementos.append(Spacer(1, 7 * mm))

    # Encabezados de la tabla
    encabezados = [
        "N.º",
        "DNI",
        "Nombres",
        "Apellidos",
        "Teléfono",
        "Correo",
        "Estado",
    ]

    datos = [
        [Paragraph(texto, estilo_encabezado)
         for texto in encabezados]
    ]

    # Obtener clientes ordenados
    clientes = Cliente.objects.all().order_by(
        "apellidos",
        "nombres",
    )

    for numero, cliente in enumerate(clientes, start=1):
        estado = (
            "Activo"
            if cliente.estado == "A"
            else "Inactivo"
        )

        fila = [
            str(numero),
            str(cliente.dni),
            Paragraph(
                str(cliente.nombres),
                estilo_celda,
            ),
            Paragraph(
                str(cliente.apellidos),
                estilo_celda,
            ),
            str(cliente.telefono),
            Paragraph(
                str(cliente.correo),
                estilo_celda,
            ),
            estado,
        ]

        datos.append(fila)

    # Anchos adaptados a A4 horizontal
    anchos = [
        12 * mm,
        22 * mm,
        34 * mm,
        42 * mm,
        25 * mm,
        65 * mm,
        22 * mm,
    ]

    tabla = Table(
        datos,
        colWidths=anchos,
        repeatRows=1,
        hAlign="CENTER",
    )

    # Estilos de la tabla
    estilos_tabla = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#0B3A75"),
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white,
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor("#B8C7D9"),
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "ALIGN",
            (0, 0),
            (1, -1),
            "CENTER",
        ),
        (
            "ALIGN",
            (4, 1),
            (4, -1),
            "CENTER",
        ),
        (
            "ALIGN",
            (6, 1),
            (6, -1),
            "CENTER",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            7,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            7,
        ),
    ]

    # Alternar colores de las filas
    for fila in range(1, len(datos)):
        if fila % 2 == 0:
            estilos_tabla.append(
                (
                    "BACKGROUND",
                    (0, fila),
                    (-1, fila),
                    colors.HexColor("#EAF1F8"),
                )
            )
        else:
            estilos_tabla.append(
                (
                    "BACKGROUND",
                    (0, fila),
                    (-1, fila),
                    colors.white,
                )
            )

    tabla.setStyle(TableStyle(estilos_tabla))

    elementos.append(tabla)
    elementos.append(Spacer(1, 8 * mm))

    # Pie del documento
    elementos.append(
        Paragraph(
            "Banco Python - Sistema Bancario Administrativo",
            estilos["Normal"],
        )
    )

    doc.build(elementos)

    return response

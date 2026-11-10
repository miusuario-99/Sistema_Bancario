from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Cuenta, CorrelativoCuenta
from clientes.models import Cliente
from .forms import CuentaForm
from django.db.models import Sum
from openpyxl import Workbook
from django.http import HttpResponse
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.conf import settings
from datetime import datetime
import os
from auditoria.utils import registrar_auditoria
from usuarios.decorators import grupos_permitidos
from decimal import Decimal
from django.db import transaction
from django.db import IntegrityError

# ==========================
# LISTAR CUENTAS
# ==========================

@grupos_permitidos("Administrador", "Supervisor", "Cajero")
def lista_cuentas(request):

    query = request.GET.get("q", "")

    # Obtener cuentas
    cuentas = Cuenta.objects.select_related(
        "cliente"
    ).order_by("-fecha_apertura")


    # BUSCADOR
    if query:

        cuentas = cuentas.filter(

            Q(numero_cuenta__icontains=query) |

            Q(cliente__nombres__icontains=query) |

            Q(cliente__apellidos__icontains=query)

        )

    # PAGINACIÓN
    paginator = Paginator(cuentas, 5)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    # ESTADÍSTICAS

    total_cuentas = Cuenta.objects.count()

    cuentas_activas = Cuenta.objects.filter(
        estado="A"
    ).count()

    cuentas_inactivas = Cuenta.objects.filter(
        estado="I"
    ).count()

    saldo_total = Cuenta.objects.aggregate(
        total=Sum("saldo")
    )["total"] or 0

    return render(request, "cuentas/lista.html", {
        "page_obj": page_obj,
        "query": query,
        "total_cuentas": total_cuentas,
        "cuentas_activas": cuentas_activas,
        "cuentas_inactivas": cuentas_inactivas,
        "saldo_total": saldo_total,
    })

    # ==========================
    # NUEVA CUENTA
    # ==========================

@grupos_permitidos("Administrador")
def nueva_cuenta(request):

    if request.method == "POST":

        form = CuentaForm(request.POST)

        if form.is_valid():

            try:
                with transaction.atomic():

                    contador = (
                        CorrelativoCuenta.objects
                        .select_for_update()
                        .get(clave="cuenta")
                    )

                    contador.ultimo_numero += 1
                    numero_generado = f"CTA-{contador.ultimo_numero:06d}"

                    contador.save(update_fields=["ultimo_numero"])

                    cuenta = form.save(commit=False)
                    cuenta.numero_cuenta = numero_generado
                    cuenta.saldo = Decimal("0.00")
                    cuenta.save()

                    registrar_auditoria(
                        request,
                        "Cuentas",
                        "Nueva cuenta",
                        f"Cuenta {cuenta.numero_cuenta} creada para {cuenta.cliente}"
                    )

                messages.success(
                    request,
                    "Cuenta creada correctamente."
                )

                return redirect("lista_cuentas")

            except IntegrityError:

                messages.error(
                    request,
                    "No se pudo crear la cuenta por un conflicto de integridad. Intente nuevamente."
                )

    else:

        form = CuentaForm()

    return render(
        request,
        "cuentas/formulario.html",
        {
            "form": form,
            "titulo": "Nueva Cuenta"
        }
    )

    # ==========================
    # EDITAR CUENTA
    # ==========================

@grupos_permitidos("Administrador")
def editar_cuenta(request, id):

    try:
        with transaction.atomic():

            cuenta = get_object_or_404(
                Cuenta.objects.select_for_update(),
                id=id
            )

            # No permitir editar cuentas inactivas.
            if cuenta.estado == "I":
                messages.error(
                    request,
                    "No se puede editar una cuenta inactiva."
                )
                return redirect("lista_cuentas")

            if request.method == "POST":

                form = CuentaForm(
                    request.POST,
                    instance=cuenta
                )

                if form.is_valid():

                    cuenta_actualizada = form.save(commit=False)

                    # Conservar los valores protegidos.
                    cuenta_actualizada.numero_cuenta = cuenta.numero_cuenta
                    cuenta_actualizada.saldo = cuenta.saldo
                    cuenta_actualizada.estado = cuenta.estado

                    cuenta_actualizada.save()

                    registrar_auditoria(
                        request,
                        "Cuentas",
                        "Editar cuenta",
                        f"Cuenta {cuenta.numero_cuenta}"
                    )

                    messages.success(
                        request,
                        "Cuenta actualizada correctamente."
                    )

                    return redirect("lista_cuentas")

            else:
                form = CuentaForm(instance=cuenta)

    except IntegrityError:
        messages.error(
            request,
            "No se pudo actualizar la cuenta por un conflicto de integridad."
        )
        return redirect("lista_cuentas")

    return render(
        request,
        "cuentas/formulario.html",
        {
            "form": form,
            "titulo": "Editar Cuenta"
        }
    )

@grupos_permitidos("Administrador")
def eliminar_cuenta(request, id):

    if request.method != "POST":
        messages.error(
            request,
            "La desactivación requiere una solicitud POST."
        )
        return redirect("lista_cuentas")
    try:

        with transaction.atomic():

            cuenta = get_object_or_404(
                Cuenta.objects.select_for_update(),
                id=id
            )

            # Comprobar si la cuenta ya está inactiva.
            if cuenta.estado == "I":
                messages.warning(
                    request,
                    "La cuenta ya se encuentra inactiva."
                )
                return redirect("lista_cuentas")

            # No desactivar cuentas que tengan saldo pendiente.
            if cuenta.saldo != Decimal("0.00"):
                messages.error(
                    request,
                    f"No se puede desactivar la cuenta "
                    f"{cuenta.numero_cuenta} porque tiene un saldo "
                    f"de S/ {cuenta.saldo:.2f}. "
                    "El saldo debe ser cero."
                )
                return redirect("lista_cuentas")

            numero_cuenta = cuenta.numero_cuenta
            cliente = cuenta.cliente

            # Registrar la operación en auditoría.
            registrar_auditoria(
                request,
                "Cuentas",
                "Desactivar cuenta",
                f"Cuenta {numero_cuenta} desactivada. "
                f"Cliente: {cliente}. Saldo: S/ {cuenta.saldo:.2f}"
            )

            # Desactivación lógica: no se elimina el registro.
            cuenta.estado = "I"
            cuenta.save(update_fields=["estado"])

    except IntegrityError:
        messages.error(
            request,
            "No se pudo desactivar la cuenta por un conflicto de integridad."
        )
        return redirect("lista_cuentas")

    messages.success(
        request,
        f"La cuenta {numero_cuenta} se desactivó correctamente. "
        "Su historial bancario se ha conservado."
    )

    return redirect("lista_cuentas")
# ==========================
# EXPORTAR CUENTAS A EXCEL
# ==========================

@grupos_permitidos("Administrador", "Supervisor")
def exportar_cuentas_excel(request):

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "Cuentas"

    # ENCABEZADOS
    ws.append([
        "N.º",
        "Número de cuenta",
        "Cliente",
        "Tipo",
        "Saldo",
        "Fecha de apertura",
        "Estado",
    ])

    cuentas = list(
        Cuenta.objects
        .select_related("cliente")
        .order_by("numero_cuenta")
    )

    for numero, cuenta in enumerate(cuentas, start=1):
        ws.append([
            numero,
            cuenta.numero_cuenta,
            f"{cuenta.cliente.nombres} {cuenta.cliente.apellidos}",
            cuenta.get_tipo_cuenta_display(),
            float(cuenta.saldo),
            cuenta.fecha_apertura.strftime("%d/%m/%Y")
                if cuenta.fecha_apertura else "",
            cuenta.get_estado_display(),
        ])

    ultima_fila = ws.max_row

    # FORMATO DEL ENCABEZADO
    for celda in ws[1]:
        celda.font = Font(
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

    ws.row_dimensions[1].height = 25

    # FORMATO DE LAS FILAS
    borde = Side(style="thin", color="D9E2F3")

    for fila in ws.iter_rows(
        min_row=2,
        max_row=ultima_fila
    ):
        for celda in fila:
            celda.border = Border(
                bottom=borde
            )
            celda.alignment = Alignment(
                vertical="center"
            )

        # Saldo en soles
        fila[4].number_format = '"S/." #,##0.00'

        # Centrar número, fecha y estado
        for indice in (0, 5, 6):
            fila[indice].alignment = Alignment(
                horizontal="center",
                vertical="center"
            )

    total_saldo = sum(
        (cuenta.saldo for cuenta in cuentas),
        Decimal("0.00")
    )

    # RESUMEN
    fila_resumen = ultima_fila + 2

    ws.cell(fila_resumen + 1, 5, float(total_saldo))

    ws.cell(fila_resumen, 1, "Total de cuentas:")
    ws.cell(fila_resumen, 2, len(cuentas))

    ws.cell(fila_resumen + 1, 1, "Saldo total:")
    ws.cell(fila_resumen + 1, 5,
            float(total_saldo))

    ws.cell(
        fila_resumen + 1, 5
    ).number_format = '"S/." #,##0.00'

    for fila in (fila_resumen, fila_resumen + 1):
        for celda in ws[fila]:
            celda.font = Font(bold=True)

    # ANCHOS DE COLUMNAS
    anchos = {
        "A": 8,
        "B": 22,
        "C": 38,
        "D": 22,
        "E": 18,
        "F": 22,
        "G": 16,
    }

    for columna, ancho in anchos.items():
        ws.column_dimensions[columna].width = ancho

    # FILTROS Y ENCABEZADO FIJO
    ws.auto_filter.ref = f"A1:G{ultima_fila}"
    ws.freeze_panes = "A2"

    # RESPUESTA EXCEL
    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        'attachment; filename="cuentas.xlsx"'
    )

    wb.save(response)

    return response

# ==========================
# EXPORTAR CUENTAS PDF
# ==========================

@grupos_permitidos("Administrador", "Supervisor")
def exportar_cuentas_pdf(request):
    response = HttpResponse(content_type="application/pdf")

    response["Content-Disposition"] = (
        'attachment; filename="cuentas.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=letter
    )

    elementos = []

    estilos = getSampleStyleSheet()

    # ==========================
    # LOGO
    # ==========================

    ruta_logo = os.path.join(
        settings.BASE_DIR,
        "static",
        "img",
        "logo_banco.png"
    )

    if os.path.exists(ruta_logo):

        logo = Image(
            ruta_logo,
            width=80,
            height=80
        )

        elementos.append(logo)

    elementos.append(Spacer(1, 10))

    # ==========================
    # TITULO
    # ==========================

    elementos.append(
        Paragraph(
            "Banco Python",
            estilos["Title"]
        )
    )

    elementos.append(
        Paragraph(
            "Reporte General de Cuentas",
            estilos["Heading2"]
        )
    )

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos.append(
        Paragraph(
            f"Fecha de emisión: {fecha}",
            estilos["Normal"]
        )
    )

    elementos.append(Spacer(1,20))

    # ==========================
    # TABLA
    # ==========================

    datos = [[
        "N.º",
        "Número de cuenta",
        "Cliente",
        "Tipo de cuenta",
        "Saldo (S/)",
        "Estado"
    ]]

    cuentas = list(
        Cuenta.objects.select_related("cliente")
    )

    cuentas = list(
        Cuenta.objects
        .select_related("cliente")
        .order_by("numero_cuenta")
    )

    contador = 1

    for cuenta in cuentas:

        datos.append([
            contador,
            cuenta.numero_cuenta,
            f"{cuenta.cliente.nombres} {cuenta.cliente.apellidos}",
            cuenta.get_tipo_cuenta_display(),
            f"S/. {cuenta.saldo:,.2f}",
            cuenta.get_estado_display()
        ])

        contador += 1

    tabla = Table(
        datos,
        repeatRows=1,
        colWidths=[30, 95, 125, 75, 65, 60]
    )

    tabla.setStyle(TableStyle([

        ("BACKGROUND",(0,0),(-1,0),colors.darkblue),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("BOTTOMPADDING",(0,0),(-1,0),10),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,1),(-1,-1),8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.whitesmoke, colors.white]),

    ]))

    elementos.append(tabla)

    elementos.append(Spacer(1,20))

    elementos.append(

        Paragraph(

            f"Total de cuentas: {len(cuentas)}",

            estilos["Normal"]

        )

    )

    doc.build(elementos)

    return response

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Spacer
from datetime import datetime
from reportlab.lib.units import cm


def encabezado_reporte(titulo):

    estilos = getSampleStyleSheet()

    elementos = []

    elementos.append(
        Paragraph(
            "<font size='18'><b>BANCO PYTHON</b></font>",
            estilos["Title"]
        )
    )

    elementos.append(
        Paragraph(
            "Sistema de Gestión Bancaria",
            estilos["Heading2"]
        )
    )

    elementos.append(
        Paragraph(
            f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            estilos["Normal"]
        )
    )

    elementos.append(Spacer(1, 15))

    elementos.append(
        Paragraph(
            f"<b>{titulo}</b>",
            estilos["Title"]
        )
    )

    elementos.append(Spacer(1, 20))

    return elementos

def pie_pagina(canvas, doc):
    """
    Dibuja el pie de página en todos los reportes PDF.
    """
    canvas.saveState()

    canvas.setFont("Helvetica", 9)

    canvas.drawString(
        2 * cm,
        1 * cm,
        "Banco Python © 2026 - Sistema de Gestión Bancaria"
    )

    canvas.drawRightString(
        19 * cm,
        1 * cm,
        f"Página {doc.page}"
    )

    canvas.restoreState()
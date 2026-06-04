import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class ReportService:
    @staticmethod
    def generar_pdf(datos_inventario, pdf_path=None, filtros=None):
        """
        Genera un reporte PDF con el resumen de inventario por producto y lote.
        datos_inventario: Lista de diccionarios que contienen las llaves:
            - 'producto_visible' (o 'producto_interno')
            - 'lote'
            - 'precio_unitario'
            - 'unidades_registradas'
            - 'total_lote'
        pdf_path: Ruta donde guardar el archivo PDF.
        filtros: Diccionario con los filtros aplicados (productos, fecha_inicio, fecha_fin).
        """
        if not pdf_path:
            pdf_dir = "reports/pdf"
            os.makedirs(pdf_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_inventario_{timestamp}.pdf"
            pdf_path = os.path.join(pdf_dir, filename)
        else:
            # Asegurar que el directorio de destino exista si viene especificado
            pdf_dir = os.path.dirname(pdf_path)
            if pdf_dir:
                os.makedirs(pdf_dir, exist_ok=True)
        
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=letter,
            rightMargin=40, 
            leftMargin=40,
            topMargin=40, 
            bottomMargin=40
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados para dar un aspecto sumamente profesional (Slate / Teal)
        title_style = ParagraphStyle(
            'ReportTitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=5
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitleStyle',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1ABC9C'),
            spaceAfter=15
        )
        
        meta_style = ParagraphStyle(
            'ReportMetaStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#7F8C8D')
        )
        
        filter_title_style = ParagraphStyle(
            'FilterTitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2C3E50'),
            fontName='Helvetica-Bold'
        )
        
        filter_text_style = ParagraphStyle(
            'FilterTextStyle',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#34495E')
        )

        footer_style = ParagraphStyle(
            'ReportFooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#95A5A6'),
            alignment=1
        )

        # Encabezado del reporte
        story.append(Paragraph("Sistema de Inventario Automático", title_style))
        story.append(Paragraph("Reporte de Inventario de Productos", subtitle_style))
        story.append(Paragraph(f"Fecha de Emisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        story.append(Spacer(1, 10))
        
        # Filtros Aplicados
        if filtros:
            story.append(Paragraph("Filtros Aplicados:", filter_title_style))
            prod_str = ", ".join(filtros.get('productos', []))
            f_ini = filtros.get('fecha_inicio', 'No definida')
            f_fin = filtros.get('fecha_fin', 'No definida')
            story.append(Paragraph(f"• <b>Productos:</b> {prod_str}", filter_text_style))
            story.append(Paragraph(f"• <b>Rango de Fechas:</b> {f_ini}  a  {f_fin}", filter_text_style))
            story.append(Spacer(1, 15))
            
        # Estructurar los datos para la tabla
        # Fila de cabecera de la tabla (evitando el término "detecciones")
        table_data = [["Producto", "Lote", "Precio Unitario", "Unidades Registradas", "Total del Lote"]]
        
        total_unidades = 0
        total_monetario = 0.0
        
        for item in datos_inventario:
            # Soporte para campos de inventario y reporte
            producto = item.get('producto_visible') or item.get('producto') or 'N/A'
            lote = item.get('lote', 'N/A')
            
            # Obtener precio unitario
            precio_u = item.get('precio_unitario', 0.0)
            
            # Unidades registradas
            unidades = item.get('unidades_registradas') or item.get('conteo') or 0
            
            # Total lote
            total_l = item.get('total_lote')
            if total_l is None:
                total_l = precio_u * unidades
                
            table_data.append([
                producto, 
                f"Lote #{lote}", 
                f"Q {precio_u:.2f}", 
                str(unidades), 
                f"Q {total_l:.2f}"
            ])
            total_unidades += unidades
            total_monetario += total_l
            
        # Fila final de totales
        table_data.append(["TOTAL GENERAL", "", "", str(total_unidades), f"Q {total_monetario:.2f}"])
        
        # Configurar la tabla de ReportLab
        # Ancho total disponible en carta es de ~532pt
        t = Table(table_data, colWidths=[150, 80, 90, 110, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            # Filas de datos
            ('BACKGROUND', (0,1), (-1,-2), colors.HexColor('#ECF0F1')),
            ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#BDC3C7')),
            ('FONTSIZE', (0,1), (-1,-2), 9),
            # Fila de totales
            ('LINEABOVE', (0,-1), (-1,-1), 1.5, colors.HexColor('#2C3E50')),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,-1), (-1,-1), 10),
            ('TOPPADDING', (0,-1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 8),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 30))
        
        # Mensaje de cierre de auditoría
        story.append(Paragraph("Este reporte es un documento generado de forma automática por el sistema de visión artificial.", meta_style))
        story.append(Spacer(1, 150))
        story.append(Paragraph("© 2026 Sistema de Inventario Automático. Mesoamérica - Teoría de Sistemas.", footer_style))
        
        doc.build(story)
        return pdf_path

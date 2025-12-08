"""
Report generation service for Excel and PDF exports
"""

import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
import database


def generate_excel_report():
    """Generate Excel report with all invoices and VAT summary"""
    
    # Get all invoices
    invoices = database.get_all_invoices(order_by='vat_period, date')
    vat_summary = database.get_vat_summary_by_period()
    
    # Create workbook
    wb = Workbook()
    
    # Sheet 1: All Invoices
    ws1 = wb.active
    ws1.title = "All Invoices"
    
    # Add title
    ws1['A1'] = "VAT Invoice Report"
    ws1['A1'].font = Font(size=14, bold=True)
    ws1.merge_cells('A1:H1')
    
    ws1['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws1['A2'].font = Font(size=10, italic=True)
    ws1.merge_cells('A2:H2')
    
    # Add headers
    headers = ['Invoice #', 'Date', 'Supplier/Customer', 'Type', 'Net', 'VAT', 'Total', 'Period']
    header_row = 4
    
    for col, header in enumerate(headers, start=1):
        cell = ws1.cell(row=header_row, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Add invoice data
    row = header_row + 1
    for invoice in invoices:
        ws1.cell(row=row, column=1, value=invoice.get('invoice_number', ''))
        ws1.cell(row=row, column=2, value=invoice.get('date', ''))
        ws1.cell(row=row, column=3, value=invoice.get('supplier_customer', ''))
        ws1.cell(row=row, column=4, value=invoice.get('invoice_type', '').capitalize())
        ws1.cell(row=row, column=5, value=float(invoice['net_amount']))
        ws1.cell(row=row, column=6, value=float(invoice['vat_amount']))
        ws1.cell(row=row, column=7, value=float(invoice['total_amount']))
        ws1.cell(row=row, column=8, value=invoice.get('vat_period', ''))
        row += 1
    
    # Auto-size columns
    for col in range(1, 9):
        ws1.column_dimensions[chr(64 + col)].width = 15
    
    # Sheet 2: VAT Summary by Period
    ws2 = wb.create_sheet(title="VAT Summary")
    
    ws2['A1'] = "VAT Summary by Period"
    ws2['A1'].font = Font(size=14, bold=True)
    ws2.merge_cells('A1:E1')
    
    # Add headers
    summary_headers = ['Period', 'Invoices', 'Sales VAT', 'Purchase VAT', 'Net VAT']
    for col, header in enumerate(summary_headers, start=1):
        cell = ws2.cell(row=3, column=col)
        cell.value = header
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Add summary data
    row = 4
    for period in vat_summary:
        ws2.cell(row=row, column=1, value=period['vat_period'])
        ws2.cell(row=row, column=2, value=period['invoice_count'])
        ws2.cell(row=row, column=3, value=float(period['sales_vat']))
        ws2.cell(row=row, column=4, value=float(period['purchase_vat']))
        ws2.cell(row=row, column=5, value=float(period['net_vat']))
        row += 1
    
    # Auto-size columns
    for col in range(1, 6):
        ws2.column_dimensions[chr(64 + col)].width = 18
    
    # Save to BytesIO
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return output


def generate_pdf_report():
    """Generate PDF report with professional formatting"""
    
    # Get data
    invoices = database.get_all_invoices(order_by='vat_period, date')
    vat_summary = database.get_vat_summary_by_period()
    
    # Create PDF
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4))
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = styles['Title']
    title_style.alignment = TA_CENTER
    title = Paragraph("VAT Invoice Report", title_style)
    story.append(title)
    
    # Date
    date_text = Paragraph(
        f"<para align=center>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</para>",
        styles['Normal']
    )
    story.append(date_text)
    story.append(Spacer(1, 0.3 * inch))
    
    # Section 1: VAT Summary
    section_title = Paragraph("<para align=left><b>VAT Summary by Period</b></para>", styles['Heading2'])
    story.append(section_title)
    story.append(Spacer(1, 0.2 * inch))
    
    # VAT Summary Table
    summary_data = [['Period', 'Invoices', 'Sales VAT (£)', 'Purchase VAT (£)', 'Net VAT (£)']]
    for period in vat_summary:
        summary_data.append([
            period['vat_period'],
            str(period['invoice_count']),
            f"{period['sales_vat']:.2f}",
            f"{period['purchase_vat']:.2f}",
            f"{period['net_vat']:.2f}"
        ])
    
    summary_table = Table(summary_data, colWidths=[1.5*inch, 1*inch, 1.2*inch, 1.3*inch, 1.2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * inch))
    
    # Section 2: All Invoices
    section_title2 = Paragraph("<para align=left><b>All Invoices</b></para>", styles['Heading2'])
    story.append(section_title2)
    story.append(Spacer(1, 0.2 * inch))
    
    # Invoice Table
    invoice_data = [['Invoice #', 'Date', 'Supplier/Customer', 'Type', 'Net (£)', 'VAT (£)', 'Total (£)', 'Period']]
    
    for invoice in invoices:
        invoice_data.append([
            invoice.get('invoice_number', '')[:15],  # Truncate if too long
            invoice.get('date', ''),
            invoice.get('supplier_customer', '')[:20],  # Truncate if too long
            invoice.get('invoice_type', '').capitalize()[:4],
            f"{invoice['net_amount']:.2f}",
            f"{invoice['vat_amount']:.2f}",
            f"{invoice['total_amount']:.2f}",
            invoice.get('vat_period', '')
        ])
    
    invoice_table = Table(invoice_data, colWidths=[1*inch, 0.8*inch, 1.3*inch, 0.6*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    story.append(invoice_table)
    
    # Build PDF
    doc.build(story)
    output.seek(0)
    
    return output

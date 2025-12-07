"""Report generation service for Excel and PDF exports"""

import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from ..database.repositories import InvoiceRepository, VATPeriodRepository
from ..database.connection import get_db_manager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:
    """Service for generating Excel and PDF reports"""

    def __init__(self):
        self.db_manager = get_db_manager()

    def generate_excel_report(
        self,
        report_type: str,
        period_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country_code: Optional[str] = None
    ) -> io.BytesIO:
        """Generate Excel report"""
        logger.info(f"Generating Excel report: {report_type}")

        # Get invoice data
        invoices = self._get_invoices_for_report(
            report_type, period_id, start_date, end_date, country_code
        )

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "VAT Report"

        # Add title
        report_title = self._get_report_title(report_type, period_id, start_date, end_date, country_code)
        ws['A1'] = report_title
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:J1')

        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A2'].font = Font(size=10, italic=True)
        ws.merge_cells('A2:J2')

        # Add headers
        headers = [
            'Invoice Number', 'Invoice Date', 'Transaction ID', 'Customer Name',
            'Country', 'Category', 'Base Amount', 'VAT Rate', 'VAT Amount', 'Total Amount'
        ]

        header_row = 4
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal='center', vertical='center')

        # Add invoice data
        row = header_row + 1
        for invoice in invoices:
            ws.cell(row=row, column=1, value=invoice['invoice_number'])
            ws.cell(row=row, column=2, value=invoice['invoice_date'])
            ws.cell(row=row, column=3, value=invoice['transaction_id'])
            ws.cell(row=row, column=4, value=invoice.get('customer_name', ''))
            ws.cell(row=row, column=5, value=invoice['country_code'])
            ws.cell(row=row, column=6, value=invoice['category'])
            ws.cell(row=row, column=7, value=float(invoice['amount']))
            ws.cell(row=row, column=8, value=f"{float(invoice['vat_rate'])}%")
            ws.cell(row=row, column=9, value=float(invoice['vat_amount']))
            ws.cell(row=row, column=10, value=float(invoice['total_amount']))
            row += 1

        # Add summary section
        summary_row = row + 2
        ws.cell(row=summary_row, column=1, value="SUMMARY").font = Font(bold=True, size=12)

        # Calculate totals
        total_base = sum(float(inv['amount']) for inv in invoices)
        total_vat = sum(float(inv['vat_amount']) for inv in invoices)
        total_amount = sum(float(inv['total_amount']) for inv in invoices)

        summary_row += 1
        ws.cell(row=summary_row, column=1, value="Total Invoices:")
        ws.cell(row=summary_row, column=2, value=len(invoices))

        summary_row += 1
        ws.cell(row=summary_row, column=1, value="Total Base Amount:")
        ws.cell(row=summary_row, column=2, value=total_base)

        summary_row += 1
        ws.cell(row=summary_row, column=1, value="Total VAT Amount:")
        ws.cell(row=summary_row, column=2, value=total_vat)

        summary_row += 1
        ws.cell(row=summary_row, column=1, value="Total Amount:")
        ws.cell(row=summary_row, column=2, value=total_amount)
        ws.cell(row=summary_row, column=2).font = Font(bold=True)

        # Country breakdown if applicable
        if report_type != 'country':
            country_breakdown = {}
            for inv in invoices:
                cc = inv['country_code']
                if cc not in country_breakdown:
                    country_breakdown[cc] = {'count': 0, 'vat': 0.0}
                country_breakdown[cc]['count'] += 1
                country_breakdown[cc]['vat'] += float(inv['vat_amount'])

            summary_row += 2
            ws.cell(row=summary_row, column=1, value="VAT by Country:").font = Font(bold=True)
            summary_row += 1
            ws.cell(row=summary_row, column=1, value="Country")
            ws.cell(row=summary_row, column=2, value="Invoices")
            ws.cell(row=summary_row, column=3, value="VAT Amount")

            for country, data in sorted(country_breakdown.items()):
                summary_row += 1
                ws.cell(row=summary_row, column=1, value=country)
                ws.cell(row=summary_row, column=2, value=data['count'])
                ws.cell(row=summary_row, column=3, value=data['vat'])

        # Auto-size columns
        for col in range(1, 11):
            ws.column_dimensions[chr(64 + col)].width = 15

        # Save to BytesIO
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return output

    def generate_pdf_report(
        self,
        report_type: str,
        period_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country_code: Optional[str] = None
    ) -> io.BytesIO:
        """Generate PDF report"""
        logger.info(f"Generating PDF report: {report_type}")

        # Get invoice data
        invoices = self._get_invoices_for_report(
            report_type, period_id, start_date, end_date, country_code
        )

        # Create PDF
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4))
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#366092'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        # Title
        report_title = self._get_report_title(report_type, period_id, start_date, end_date, country_code)
        elements.append(Paragraph(report_title, title_style))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))

        # Invoice table
        table_data = [[
            'Invoice #', 'Date', 'Customer', 'Country',
            'Category', 'Base', 'VAT Rate', 'VAT', 'Total'
        ]]

        for inv in invoices:
            table_data.append([
                inv['invoice_number'],
                inv['invoice_date'],
                (inv.get('customer_name', '') or '')[:15],
                inv['country_code'],
                inv['category'][:8],
                f"€{float(inv['amount']):.2f}",
                f"{float(inv['vat_rate']):.0f}%",
                f"€{float(inv['vat_amount']):.2f}",
                f"€{float(inv['total_amount']):.2f}"
            ])

        # Create table
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)
        elements.append(PageBreak())

        # Summary page
        elements.append(Paragraph("Summary", title_style))
        elements.append(Spacer(1, 20))

        total_base = sum(float(inv['amount']) for inv in invoices)
        total_vat = sum(float(inv['vat_amount']) for inv in invoices)
        total_amount = sum(float(inv['total_amount']) for inv in invoices)

        summary_data = [
            ['Metric', 'Value'],
            ['Total Invoices', str(len(invoices))],
            ['Total Base Amount', f"€{total_base:.2f}"],
            ['Total VAT Amount', f"€{total_vat:.2f}"],
            ['Total Amount', f"€{total_amount:.2f}"]
        ]

        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))

        elements.append(summary_table)
        elements.append(Spacer(1, 30))

        # Country breakdown
        if report_type != 'country':
            elements.append(Paragraph("VAT Breakdown by Country", styles['Heading2']))
            elements.append(Spacer(1, 10))

            country_breakdown = {}
            for inv in invoices:
                cc = inv['country_code']
                if cc not in country_breakdown:
                    country_breakdown[cc] = {'count': 0, 'vat': 0.0}
                country_breakdown[cc]['count'] += 1
                country_breakdown[cc]['vat'] += float(inv['vat_amount'])

            country_data = [['Country', 'Invoice Count', 'VAT Amount']]
            for country, data in sorted(country_breakdown.items()):
                country_data.append([
                    country,
                    str(data['count']),
                    f"€{data['vat']:.2f}"
                ])

            country_table = Table(country_data, colWidths=[2*inch, 2*inch, 2*inch])
            country_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))

            elements.append(country_table)

        # Build PDF
        doc.build(elements)
        output.seek(0)

        return output

    def _get_invoices_for_report(
        self,
        report_type: str,
        period_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get invoices based on report parameters"""
        with self.db_manager.session_scope() as session:
            invoice_repo = InvoiceRepository(session)

            if report_type == 'period' and period_id:
                invoices = invoice_repo.filter(vat_period_id=period_id)
            elif report_type == 'daterange' and start_date and end_date:
                invoices = invoice_repo.filter(start_date=start_date, end_date=end_date)
            elif report_type == 'country' and country_code:
                invoices = invoice_repo.filter(country_code=country_code)
            else:  # all
                invoices = invoice_repo.filter()

            return [inv.to_dict() for inv in invoices]

    def _get_report_title(
        self,
        report_type: str,
        period_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        country_code: Optional[str] = None
    ) -> str:
        """Generate report title"""
        if report_type == 'period' and period_id:
            with self.db_manager.session_scope() as session:
                period_repo = VATPeriodRepository(session)
                period = period_repo.get_by_id(period_id)
                if period:
                    return f"VAT Report - {period.period_name}"
            return "VAT Period Report"
        elif report_type == 'daterange':
            return f"VAT Report - {start_date} to {end_date}"
        elif report_type == 'country':
            country_name = country_code if country_code else "All Countries"
            return f"VAT Report - {country_name}"
        else:
            return "VAT Report - All Invoices"

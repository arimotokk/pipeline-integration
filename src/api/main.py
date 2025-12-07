"""FastAPI main application for VAT Integration Pipeline Phase 2"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import tempfile
import os
from pathlib import Path

from ..services.batch_upload_service import BatchUploadService
from ..services.vat_period_service import VATPeriodService
from ..services.report_service import ReportService
from ..database.repositories import InvoiceRepository
from ..database.connection import get_db_manager, get_db_session
from ..utils.logger import get_logger


logger = get_logger(__name__)

# Setup Jinja2 templates
templates_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Create FastAPI app
app = FastAPI(
    title="VAT Integration Pipeline API",
    description="Phase 3 API with web UI, batch uploads, VAT period management, and reporting",
    version="3.0.0"
)

# Initialize services
batch_service = BatchUploadService()
period_service = VATPeriodService()
report_service = ReportService()


# Pydantic models for request/response
class InvoiceFilter(BaseModel):
    country_code: Optional[str] = None
    category: Optional[str] = None
    vat_period_id: Optional[int] = None
    batch_upload_id: Optional[int] = None
    validation_status: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    skip: int = 0
    limit: int = 100


class CreatePeriodsRequest(BaseModel):
    year: int
    period_type: str  # 'monthly' or 'quarterly'


class ClosePeriodRequest(BaseModel):
    closed_by: str = 'api_user'


class SubmitPeriodRequest(BaseModel):
    submitted_by: str = 'api_user'


# Health check
@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "name": "VAT Integration Pipeline API",
        "version": "3.0.0",
        "status": "healthy",
        "phase": "3",
        "features": [
            "Batch Upload Processing",
            "VAT Period Management",
            "Invoice Filtering & Search",
            "Web UI Dashboard",
            "Manual Data Entry",
            "Error Dashboard",
            "Excel & PDF Reports"
        ]
    }


# Invoice endpoints
@app.get("/api/invoices")
def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session = Depends(get_db_session)
):
    """List all invoices with pagination"""
    invoice_repo = InvoiceRepository(session)
    invoices = invoice_repo.get_all(skip=skip, limit=limit)
    total = invoice_repo.count()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "invoices": [inv.to_dict() for inv in invoices]
    }


@app.post("/api/invoices/filter")
def filter_invoices(filter_params: InvoiceFilter, session = Depends(get_db_session)):
    """Filter invoices by multiple criteria"""
    invoice_repo = InvoiceRepository(session)

    invoices = invoice_repo.filter(
        country_code=filter_params.country_code,
        category=filter_params.category,
        vat_period_id=filter_params.vat_period_id,
        batch_upload_id=filter_params.batch_upload_id,
        validation_status=filter_params.validation_status,
        date_from=filter_params.date_from,
        date_to=filter_params.date_to,
        min_amount=filter_params.min_amount,
        max_amount=filter_params.max_amount,
        skip=filter_params.skip,
        limit=filter_params.limit
    )

    return {
        "count": len(invoices),
        "filters": filter_params.dict(exclude_none=True),
        "invoices": [inv.to_dict() for inv in invoices]
    }


@app.get("/api/invoices/search")
def search_invoices(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session = Depends(get_db_session)
):
    """Search invoices by invoice number, customer name, or transaction ID"""
    invoice_repo = InvoiceRepository(session)
    invoices = invoice_repo.search(q, skip=skip, limit=limit)

    return {
        "query": q,
        "count": len(invoices),
        "invoices": [inv.to_dict() for inv in invoices]
    }


@app.get("/api/invoices/{invoice_id}")
def get_invoice(invoice_id: int, session = Depends(get_db_session)):
    """Get a specific invoice by ID"""
    invoice_repo = InvoiceRepository(session)
    invoice = invoice_repo.get_by_id(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice.to_dict()


@app.get("/api/invoices/stats/summary")
def get_invoice_summary(
    country_code: Optional[str] = None,
    vat_period_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    session = Depends(get_db_session)
):
    """Get summary statistics for invoices"""
    invoice_repo = InvoiceRepository(session)
    stats = invoice_repo.get_summary_stats(
        country_code=country_code,
        vat_period_id=vat_period_id,
        date_from=date_from,
        date_to=date_to
    )

    return stats


# VAT Period endpoints
@app.post("/api/vat-periods/create")
def create_vat_periods(request: CreatePeriodsRequest):
    """Create VAT periods for a year (monthly or quarterly)"""
    if request.period_type == 'monthly':
        periods = period_service.create_monthly_periods(request.year)
    elif request.period_type == 'quarterly':
        periods = period_service.create_quarterly_periods(request.year)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid period_type. Must be 'monthly' or 'quarterly'"
        )

    return {
        "year": request.year,
        "period_type": request.period_type,
        "created_count": len(periods),
        "periods": periods
    }


@app.get("/api/vat-periods")
def list_vat_periods(
    year: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all VAT periods with optional filters"""
    periods = period_service.get_all_periods(
        year=year,
        status=status,
        skip=skip,
        limit=limit
    )

    return {
        "count": len(periods),
        "periods": periods
    }


@app.get("/api/vat-periods/open")
def list_open_periods():
    """Get all open VAT periods"""
    periods = period_service.get_open_periods()
    return {
        "count": len(periods),
        "periods": periods
    }


@app.get("/api/vat-periods/{period_id}")
def get_vat_period(period_id: int):
    """Get VAT period summary with detailed breakdown"""
    summary = period_service.get_period_summary(period_id)

    if not summary:
        raise HTTPException(status_code=404, detail="VAT period not found")

    return summary


@app.post("/api/vat-periods/{period_id}/close")
def close_vat_period(period_id: int, request: ClosePeriodRequest):
    """Close a VAT period"""
    period = period_service.close_period(period_id, request.closed_by)

    if not period:
        raise HTTPException(
            status_code=404,
            detail="VAT period not found or already closed"
        )

    return {
        "message": "VAT period closed successfully",
        "period": period
    }


@app.post("/api/vat-periods/{period_id}/submit")
def submit_vat_period(period_id: int, request: SubmitPeriodRequest):
    """Submit a VAT period to tax authority"""
    period = period_service.submit_period(period_id, request.submitted_by)

    if not period:
        raise HTTPException(
            status_code=404,
            detail="VAT period not found or not in closed status"
        )

    return {
        "message": "VAT period submitted successfully",
        "period": period
    }


# Batch Upload endpoints
@app.post("/api/batch-upload")
async def upload_batch_file(
    file: UploadFile = File(...),
    uploaded_by: str = Query('api_user'),
    auto_assign_period: bool = Query(True)
):
    """Upload and process a batch file (CSV, JSON, or Excel)"""
    # Validate file type
    allowed_extensions = ['.csv', '.json', '.xlsx']
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Save uploaded file to temp location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Process the file
        result = batch_service.process_file(
            temp_path,
            uploaded_by=uploaded_by,
            auto_assign_period=auto_assign_period
        )

        # Clean up temp file
        os.unlink(temp_path)

        return result

    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/batch-upload/{batch_id}")
def get_batch_status(batch_id: str):
    """Get status of a batch upload"""
    batch = batch_service.get_batch_status(batch_id)

    if not batch:
        raise HTTPException(status_code=404, detail="Batch upload not found")

    return batch


@app.get("/api/batch-uploads")
def list_batch_uploads(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all batch uploads"""
    batches = batch_service.get_all_batches(status=status, skip=skip, limit=limit)

    return {
        "count": len(batches),
        "batches": batches
    }


# Web UI endpoints (Phase 3)
@app.get("/ui/dashboard", response_class=HTMLResponse)
async def web_dashboard(request: Request, session = Depends(get_db_session)):
    """Web UI dashboard"""
    invoice_repo = InvoiceRepository(session)

    # Get statistics
    total_invoices = invoice_repo.count()
    stats = invoice_repo.get_summary_stats()
    failed_count = invoice_repo.count(validation_status='invalid')

    # Get recent invoices
    recent_invoices = invoice_repo.get_all(limit=10)

    # Get VAT periods
    vat_periods = period_service.get_all_periods(limit=10)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "total_invoices": total_invoices,
        "failed_count": failed_count,
        "stats": stats,
        "recent_invoices": [inv.to_dict() for inv in recent_invoices],
        "vat_periods": vat_periods
    })


@app.get("/ui/errors", response_class=HTMLResponse)
async def web_error_dashboard(request: Request, session = Depends(get_db_session)):
    """Web UI for failed invoice extractions"""
    invoice_repo = InvoiceRepository(session)

    # Get failed invoices
    failed_invoices = invoice_repo.filter(validation_status='invalid', limit=1000)

    # Calculate statistics
    total_failed = len(failed_invoices)
    total_invoices = invoice_repo.count()
    success_rate = ((total_invoices - total_failed) / total_invoices * 100) if total_invoices > 0 else 0

    return templates.TemplateResponse("error_dashboard.html", {
        "request": request,
        "failed_invoices": [inv.to_dict() for inv in failed_invoices],
        "total_failed": total_failed,
        "pending_review": total_failed,  # All failed are pending
        "resolved": 0,
        "success_rate": success_rate
    })


@app.get("/ui/manual-entry", response_class=HTMLResponse)
@app.get("/ui/manual-entry/{invoice_id}", response_class=HTMLResponse)
async def web_manual_entry(request: Request, invoice_id: Optional[int] = None, session = Depends(get_db_session)):
    """Web UI for manual data entry"""
    invoice_data = None

    if invoice_id:
        invoice_repo = InvoiceRepository(session)
        invoice = invoice_repo.get_by_id(invoice_id)
        if invoice:
            invoice_data = invoice.to_dict()

    return templates.TemplateResponse("manual_entry.html", {
        "request": request,
        "invoice": invoice_data,
        "document_url": "/static/placeholder.pdf",  # Placeholder for now
        "document_type": "pdf"
    })


@app.post("/ui/manual-entry/submit")
async def submit_manual_entry(
    request: Request,
    invoice_number: str = Form(...),
    invoice_date: str = Form(...),
    amount: float = Form(...),
    country_code: str = Form(...),
    category: str = Form(...),
    customer_name: Optional[str] = Form(None),
    transaction_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    session = Depends(get_db_session)
):
    """Submit manually entered invoice data"""
    from ..core.calculator import VATCalculator

    # Calculate VAT
    vat_calculator = VATCalculator('config/vat_rates.json')
    vat_result = vat_calculator.calculate_vat(amount, country_code, category)

    # Create invoice
    invoice_repo = InvoiceRepository(session)
    invoice_data = {
        'invoice_number': invoice_number,
        'invoice_date': invoice_date,
        'transaction_id': transaction_id or f"MANUAL-{invoice_number}",
        'amount': amount,
        'country_code': country_code,
        'category': category,
        'customer_name': customer_name,
        'description': description,
        'vat_rate': vat_result['vat_rate'],
        'vat_amount': vat_result['vat_amount'],
        'total_amount': vat_result['total_amount'],
        'validation_status': 'valid',
        'processing_status': 'completed'
    }

    # Auto-assign to VAT period
    period_repo_session = session
    from ..database.repositories import VATPeriodRepository
    period_repo = VATPeriodRepository(period_repo_session)
    period = period_repo.get_period_for_date(invoice_date)
    if period:
        invoice_data['vat_period_id'] = period.id

    invoice = invoice_repo.create(invoice_data)

    return templates.TemplateResponse("manual_entry.html", {
        "request": request,
        "success": True,
        "message": f"Invoice {invoice_number} successfully created!",
        "invoice": None,
        "document_url": "/static/placeholder.pdf",
        "document_type": "pdf"
    })


@app.get("/ui/reports", response_class=HTMLResponse)
async def web_reports(request: Request):
    """Web UI for report generation"""
    # Get VAT periods for dropdown
    vat_periods = period_service.get_all_periods(limit=100)

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "vat_periods": vat_periods
    })


@app.get("/api/reports/download")
async def download_report(
    format: str = Query(..., regex="^(excel|pdf)$"),
    type: str = Query(..., regex="^(period|daterange|country|all)$"),
    period_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    country_code: Optional[str] = None
):
    """Download report in Excel or PDF format"""
    try:
        if format == 'excel':
            output = report_service.generate_excel_report(
                report_type=type,
                period_id=period_id,
                start_date=start_date,
                end_date=end_date,
                country_code=country_code
            )

            filename = f"vat_report_{type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:  # pdf
            output = report_service.generate_pdf_report(
                report_type=type,
                period_id=period_id,
                start_date=start_date,
                end_date=end_date,
                country_code=country_code
            )

            filename = f"vat_report_{type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            return StreamingResponse(
                output,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""FastAPI main application for VAT Integration Pipeline Phase 2"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import tempfile
import os

from ..services.batch_upload_service import BatchUploadService
from ..services.vat_period_service import VATPeriodService
from ..database.repositories import InvoiceRepository
from ..database.connection import get_db_manager, get_db_session
from ..utils.logger import get_logger


logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VAT Integration Pipeline API",
    description="Phase 2 API for batch uploads, VAT period management, and invoice history",
    version="2.0.0"
)

# Initialize services
batch_service = BatchUploadService()
period_service = VATPeriodService()


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
        "version": "2.0.0",
        "status": "healthy",
        "phase": "2"
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

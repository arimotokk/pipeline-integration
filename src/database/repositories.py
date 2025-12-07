"""Repository pattern for database operations"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime

from .models import Invoice, VATPeriod, BatchUpload
from ..utils.logger import get_logger


logger = get_logger(__name__)


class InvoiceRepository:
    """Repository for invoice operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(**invoice_data)
        self.session.add(invoice)
        self.session.commit()
        self.session.refresh(invoice)
        logger.info(f"Created invoice: {invoice.invoice_number}")
        return invoice

    def create_batch(self, invoices_data: List[Dict[str, Any]]) -> List[Invoice]:
        """Create multiple invoices in batch"""
        invoices = [Invoice(**data) for data in invoices_data]
        self.session.add_all(invoices)
        self.session.commit()
        logger.info(f"Created {len(invoices)} invoices in batch")
        return invoices

    def get_by_id(self, invoice_id: int) -> Optional[Invoice]:
        """Get invoice by ID"""
        return self.session.query(Invoice).filter(Invoice.id == invoice_id).first()

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number"""
        return self.session.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = 'created_at',
        sort_order: str = 'desc'
    ) -> List[Invoice]:
        """Get all invoices with pagination"""
        query = self.session.query(Invoice).filter(Invoice.is_deleted == False)

        # Apply sorting
        if sort_order == 'desc':
            query = query.order_by(desc(getattr(Invoice, sort_by)))
        else:
            query = query.order_by(getattr(Invoice, sort_by))

        return query.offset(skip).limit(limit).all()

    def filter(
        self,
        country_code: Optional[str] = None,
        category: Optional[str] = None,
        vat_period_id: Optional[int] = None,
        batch_upload_id: Optional[int] = None,
        validation_status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """Filter invoices with multiple criteria"""
        query = self.session.query(Invoice).filter(Invoice.is_deleted == False)

        if country_code:
            query = query.filter(Invoice.country_code == country_code)

        if category:
            query = query.filter(Invoice.category == category)

        if vat_period_id:
            query = query.filter(Invoice.vat_period_id == vat_period_id)

        if batch_upload_id:
            query = query.filter(Invoice.batch_upload_id == batch_upload_id)

        if validation_status:
            query = query.filter(Invoice.validation_status == validation_status)

        if date_from:
            query = query.filter(Invoice.invoice_date >= date_from)

        if date_to:
            query = query.filter(Invoice.invoice_date <= date_to)

        if min_amount is not None:
            query = query.filter(Invoice.amount >= min_amount)

        if max_amount is not None:
            query = query.filter(Invoice.amount <= max_amount)

        return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()

    def search(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Search invoices by invoice number, customer name, or transaction ID"""
        search_pattern = f"%{search_term}%"
        query = self.session.query(Invoice).filter(
            and_(
                Invoice.is_deleted == False,
                or_(
                    Invoice.invoice_number.like(search_pattern),
                    Invoice.transaction_id.like(search_pattern),
                    Invoice.customer_name.like(search_pattern),
                    Invoice.vendor_name.like(search_pattern)
                )
            )
        )
        return query.order_by(desc(Invoice.created_at)).offset(skip).limit(limit).all()

    def update(self, invoice_id: int, update_data: Dict[str, Any]) -> Optional[Invoice]:
        """Update an invoice"""
        invoice = self.get_by_id(invoice_id)
        if invoice:
            for key, value in update_data.items():
                if hasattr(invoice, key):
                    setattr(invoice, key, value)
            invoice.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(invoice)
            logger.info(f"Updated invoice: {invoice.invoice_number}")
        return invoice

    def soft_delete(self, invoice_id: int) -> bool:
        """Soft delete an invoice"""
        invoice = self.get_by_id(invoice_id)
        if invoice:
            invoice.is_deleted = True
            invoice.updated_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Soft deleted invoice: {invoice.invoice_number}")
            return True
        return False

    def count(self, **filters) -> int:
        """Count invoices with optional filters"""
        query = self.session.query(Invoice).filter(Invoice.is_deleted == False)

        for key, value in filters.items():
            if value is not None and hasattr(Invoice, key):
                query = query.filter(getattr(Invoice, key) == value)

        return query.count()

    def get_summary_stats(
        self,
        country_code: Optional[str] = None,
        vat_period_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary statistics for invoices"""
        query = self.session.query(Invoice).filter(Invoice.is_deleted == False)

        if country_code:
            query = query.filter(Invoice.country_code == country_code)
        if vat_period_id:
            query = query.filter(Invoice.vat_period_id == vat_period_id)
        if date_from:
            query = query.filter(Invoice.invoice_date >= date_from)
        if date_to:
            query = query.filter(Invoice.invoice_date <= date_to)

        invoices = query.all()

        return {
            'total_count': len(invoices),
            'total_base_amount': sum(inv.amount for inv in invoices),
            'total_vat_amount': sum(inv.vat_amount for inv in invoices),
            'total_amount': sum(inv.total_amount for inv in invoices),
            'valid_count': sum(1 for inv in invoices if inv.validation_status == 'valid'),
            'invalid_count': sum(1 for inv in invoices if inv.validation_status != 'valid')
        }


class VATPeriodRepository:
    """Repository for VAT period operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, period_data: Dict[str, Any]) -> VATPeriod:
        """Create a new VAT period"""
        period = VATPeriod(**period_data)
        self.session.add(period)
        self.session.commit()
        self.session.refresh(period)
        logger.info(f"Created VAT period: {period.period_name}")
        return period

    def get_by_id(self, period_id: int) -> Optional[VATPeriod]:
        """Get VAT period by ID"""
        return self.session.query(VATPeriod).filter(VATPeriod.id == period_id).first()

    def get_by_name(self, period_name: str) -> Optional[VATPeriod]:
        """Get VAT period by name"""
        return self.session.query(VATPeriod).filter(
            VATPeriod.period_name == period_name
        ).first()

    def get_all(
        self,
        status: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[VATPeriod]:
        """Get all VAT periods with optional filters"""
        query = self.session.query(VATPeriod)

        if status:
            query = query.filter(VATPeriod.status == status)
        if year:
            query = query.filter(VATPeriod.year == year)

        return query.order_by(desc(VATPeriod.start_date)).offset(skip).limit(limit).all()

    def get_open_periods(self) -> List[VATPeriod]:
        """Get all open VAT periods"""
        return self.session.query(VATPeriod).filter(
            VATPeriod.status == 'open'
        ).order_by(VATPeriod.start_date).all()

    def get_period_for_date(self, date: str) -> Optional[VATPeriod]:
        """Find the VAT period that contains a specific date"""
        return self.session.query(VATPeriod).filter(
            and_(
                VATPeriod.start_date <= date,
                VATPeriod.end_date >= date
            )
        ).first()

    def update(self, period_id: int, update_data: Dict[str, Any]) -> Optional[VATPeriod]:
        """Update a VAT period"""
        period = self.get_by_id(period_id)
        if period:
            for key, value in update_data.items():
                if hasattr(period, key):
                    setattr(period, key, value)
            period.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(period)
            logger.info(f"Updated VAT period: {period.period_name}")
        return period

    def close_period(self, period_id: int, closed_by: str) -> Optional[VATPeriod]:
        """Close a VAT period"""
        period = self.get_by_id(period_id)
        if period and period.status == 'open':
            period.status = 'closed'
            period.closed_at = datetime.utcnow()
            period.submitted_by = closed_by
            self.session.commit()
            self.session.refresh(period)
            logger.info(f"Closed VAT period: {period.period_name}")
        return period

    def submit_period(self, period_id: int, submitted_by: str) -> Optional[VATPeriod]:
        """Submit a VAT period"""
        period = self.get_by_id(period_id)
        if period and period.status == 'closed':
            period.status = 'submitted'
            period.submitted_at = datetime.utcnow()
            period.submitted_by = submitted_by
            self.session.commit()
            self.session.refresh(period)
            logger.info(f"Submitted VAT period: {period.period_name}")
        return period

    def recalculate_totals(self, period_id: int) -> Optional[VATPeriod]:
        """Recalculate totals for a VAT period based on associated invoices"""
        period = self.get_by_id(period_id)
        if period:
            invoices = self.session.query(Invoice).filter(
                and_(
                    Invoice.vat_period_id == period_id,
                    Invoice.is_deleted == False,
                    Invoice.validation_status == 'valid'
                )
            ).all()

            period.total_invoices = len(invoices)
            period.total_base_amount = sum(inv.amount for inv in invoices)
            period.total_vat_amount = sum(inv.vat_amount for inv in invoices)
            period.total_amount = sum(inv.total_amount for inv in invoices)
            period.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(period)
            logger.info(f"Recalculated totals for period: {period.period_name}")
        return period


class BatchUploadRepository:
    """Repository for batch upload operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, batch_data: Dict[str, Any]) -> BatchUpload:
        """Create a new batch upload record"""
        batch = BatchUpload(**batch_data)
        self.session.add(batch)
        self.session.commit()
        self.session.refresh(batch)
        logger.info(f"Created batch upload: {batch.batch_id}")
        return batch

    def get_by_id(self, batch_id: int) -> Optional[BatchUpload]:
        """Get batch upload by ID"""
        return self.session.query(BatchUpload).filter(BatchUpload.id == batch_id).first()

    def get_by_batch_id(self, batch_id: str) -> Optional[BatchUpload]:
        """Get batch upload by batch ID"""
        return self.session.query(BatchUpload).filter(
            BatchUpload.batch_id == batch_id
        ).first()

    def get_all(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[BatchUpload]:
        """Get all batch uploads with optional status filter"""
        query = self.session.query(BatchUpload)

        if status:
            query = query.filter(BatchUpload.status == status)

        return query.order_by(desc(BatchUpload.created_at)).offset(skip).limit(limit).all()

    def update(self, batch_id: int, update_data: Dict[str, Any]) -> Optional[BatchUpload]:
        """Update a batch upload"""
        batch = self.get_by_id(batch_id)
        if batch:
            for key, value in update_data.items():
                if hasattr(batch, key):
                    setattr(batch, key, value)
            self.session.commit()
            self.session.refresh(batch)
        return batch

    def update_status(
        self,
        batch_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> Optional[BatchUpload]:
        """Update batch upload status"""
        batch = self.get_by_id(batch_id)
        if batch:
            batch.status = status
            if error_message:
                batch.error_message = error_message
            if status == 'processing' and not batch.started_at:
                batch.started_at = datetime.utcnow()
            elif status in ['completed', 'failed']:
                batch.completed_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(batch)
            logger.info(f"Updated batch {batch.batch_id} status to {status}")
        return batch

    def update_progress(
        self,
        batch_id: int,
        processed: int,
        successful: int,
        failed: int
    ) -> Optional[BatchUpload]:
        """Update batch upload processing progress"""
        batch = self.get_by_id(batch_id)
        if batch:
            batch.processed_records = processed
            batch.successful_records = successful
            batch.failed_records = failed
            self.session.commit()
            self.session.refresh(batch)
        return batch

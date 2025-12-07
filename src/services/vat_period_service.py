"""VAT Period management service"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from calendar import monthrange

from ..database.repositories import VATPeriodRepository, InvoiceRepository
from ..database.connection import get_db_manager
from ..utils.logger import get_logger


logger = get_logger(__name__)


class VATPeriodService:
    """Service for managing VAT periods"""

    def __init__(self):
        self.db_manager = get_db_manager()

    def create_quarterly_periods(self, year: int) -> List[Dict[str, Any]]:
        """
        Create quarterly VAT periods for a given year

        Args:
            year: Year for which to create periods

        Returns:
            list: Created VAT periods
        """
        quarters = [
            {'quarter': 1, 'start_month': 1, 'end_month': 3},
            {'quarter': 2, 'start_month': 4, 'end_month': 6},
            {'quarter': 3, 'start_month': 7, 'end_month': 9},
            {'quarter': 4, 'start_month': 10, 'end_month': 12}
        ]

        created_periods = []

        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)

            for q in quarters:
                period_name = f"{year}-Q{q['quarter']}"

                # Check if period already exists
                existing = period_repo.get_by_name(period_name)
                if existing:
                    logger.warning(f"Period {period_name} already exists")
                    created_periods.append(existing.to_dict())
                    continue

                # Calculate start and end dates
                start_date = f"{year}-{q['start_month']:02d}-01"
                last_day = monthrange(year, q['end_month'])[1]
                end_date = f"{year}-{q['end_month']:02d}-{last_day:02d}"

                period_data = {
                    'period_name': period_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_type': 'quarterly',
                    'year': year,
                    'quarter': q['quarter'],
                    'status': 'open'
                }

                period = period_repo.create(period_data)
                created_periods.append(period.to_dict())
                logger.info(f"Created quarterly period: {period_name}")

        return created_periods

    def create_monthly_periods(self, year: int) -> List[Dict[str, Any]]:
        """
        Create monthly VAT periods for a given year

        Args:
            year: Year for which to create periods

        Returns:
            list: Created VAT periods
        """
        created_periods = []

        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)

            for month in range(1, 13):
                period_name = f"{year}-M{month:02d}"

                # Check if period already exists
                existing = period_repo.get_by_name(period_name)
                if existing:
                    logger.warning(f"Period {period_name} already exists")
                    created_periods.append(existing.to_dict())
                    continue

                # Calculate start and end dates
                start_date = f"{year}-{month:02d}-01"
                last_day = monthrange(year, month)[1]
                end_date = f"{year}-{month:02d}-{last_day:02d}"

                period_data = {
                    'period_name': period_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'period_type': 'monthly',
                    'year': year,
                    'month': month,
                    'status': 'open'
                }

                period = period_repo.create(period_data)
                created_periods.append(period.to_dict())
                logger.info(f"Created monthly period: {period_name}")

        return created_periods

    def get_period_for_invoice_date(self, invoice_date: str) -> Optional[Dict[str, Any]]:
        """
        Get the appropriate VAT period for an invoice date

        Args:
            invoice_date: Invoice date (YYYY-MM-DD)

        Returns:
            dict: VAT period or None
        """
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)
            period = period_repo.get_period_for_date(invoice_date)
            return period.to_dict() if period else None

    def close_period(self, period_id: int, closed_by: str = 'system') -> Optional[Dict[str, Any]]:
        """
        Close a VAT period and recalculate totals

        Args:
            period_id: ID of the period to close
            closed_by: User who is closing the period

        Returns:
            dict: Closed period
        """
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)

            # Recalculate totals before closing
            period_repo.recalculate_totals(period_id)

            # Close the period
            period = period_repo.close_period(period_id, closed_by)

            if period:
                logger.info(
                    f"Closed period {period.period_name}: "
                    f"{period.total_invoices} invoices, "
                    f"€{period.total_vat_amount:.2f} VAT"
                )
                return period.to_dict()

        return None

    def submit_period(self, period_id: int, submitted_by: str) -> Optional[Dict[str, Any]]:
        """
        Submit a VAT period (mark as submitted to tax authority)

        Args:
            period_id: ID of the period to submit
            submitted_by: User submitting the period

        Returns:
            dict: Submitted period
        """
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)
            period = period_repo.submit_period(period_id, submitted_by)
            return period.to_dict() if period else None

    def get_period_summary(self, period_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed summary for a VAT period

        Args:
            period_id: Period ID

        Returns:
            dict: Period summary with invoice breakdown
        """
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)
            invoice_repo = InvoiceRepository(session)

            period = period_repo.get_by_id(period_id)
            if not period:
                return None

            # Get invoice summary stats
            invoice_stats = invoice_repo.get_summary_stats(vat_period_id=period_id)

            # Get breakdown by country
            from sqlalchemy import func
            from ..database.models import Invoice

            country_breakdown = session.query(
                Invoice.country_code,
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.amount).label('base_amount'),
                func.sum(Invoice.vat_amount).label('vat_amount')
            ).filter(
                Invoice.vat_period_id == period_id,
                Invoice.is_deleted == False,
                Invoice.validation_status == 'valid'
            ).group_by(Invoice.country_code).all()

            # Get breakdown by category
            category_breakdown = session.query(
                Invoice.category,
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.amount).label('base_amount'),
                func.sum(Invoice.vat_amount).label('vat_amount')
            ).filter(
                Invoice.vat_period_id == period_id,
                Invoice.is_deleted == False,
                Invoice.validation_status == 'valid'
            ).group_by(Invoice.category).all()

            return {
                'period': period.to_dict(),
                'summary': invoice_stats,
                'by_country': [
                    {
                        'country_code': row.country_code,
                        'count': row.count,
                        'base_amount': float(row.base_amount or 0),
                        'vat_amount': float(row.vat_amount or 0)
                    }
                    for row in country_breakdown
                ],
                'by_category': [
                    {
                        'category': row.category,
                        'count': row.count,
                        'base_amount': float(row.base_amount or 0),
                        'vat_amount': float(row.vat_amount or 0)
                    }
                    for row in category_breakdown
                ]
            }

    def get_all_periods(
        self,
        year: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all VAT periods with optional filters"""
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)
            periods = period_repo.get_all(status=status, year=year, skip=skip, limit=limit)
            return [p.to_dict() for p in periods]

    def get_open_periods(self) -> List[Dict[str, Any]]:
        """Get all open VAT periods"""
        with self.db_manager.session_scope() as session:
            period_repo = VATPeriodRepository(session)
            periods = period_repo.get_open_periods()
            return [p.to_dict() for p in periods]

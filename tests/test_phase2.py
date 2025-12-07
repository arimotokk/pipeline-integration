"""Tests for Phase 2 features"""

import pytest
import tempfile
import os
from datetime import datetime

from src.database.connection import DatabaseManager
from src.database.repositories import InvoiceRepository, VATPeriodRepository, BatchUploadRepository
from src.services.vat_period_service import VATPeriodService
from src.services.batch_upload_service import BatchUploadService


@pytest.fixture
def test_db():
    """Create a test database"""
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    db_url = f'sqlite:///{db_path}'
    db_manager = DatabaseManager(db_url)
    db_manager.create_tables()

    yield db_manager

    # Cleanup
    db_manager.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_invoice_repository(test_db):
    """Test invoice repository operations"""
    with test_db.session_scope() as session:
        repo = InvoiceRepository(session)

        # Create invoice
        invoice_data = {
            'invoice_number': 'TEST-001',
            'transaction_id': 'TXN-001',
            'amount': 100.0,
            'country_code': 'DE',
            'invoice_date': '2025-01-15',
            'category': 'standard',
            'vat_rate': 19.0,
            'vat_amount': 19.0,
            'total_amount': 119.0,
            'validation_status': 'valid'
        }

        invoice = repo.create(invoice_data)
        assert invoice.id is not None
        assert invoice.invoice_number == 'TEST-001'

        # Get by ID
        retrieved = repo.get_by_id(invoice.id)
        assert retrieved is not None
        assert retrieved.invoice_number == 'TEST-001'

        # Filter
        invoices = repo.filter(country_code='DE')
        assert len(invoices) == 1


def test_vat_period_repository(test_db):
    """Test VAT period repository operations"""
    with test_db.session_scope() as session:
        repo = VATPeriodRepository(session)

        # Create period
        period_data = {
            'period_name': '2025-Q1',
            'start_date': '2025-01-01',
            'end_date': '2025-03-31',
            'period_type': 'quarterly',
            'year': 2025,
            'quarter': 1,
            'status': 'open'
        }

        period = repo.create(period_data)
        assert period.id is not None
        assert period.period_name == '2025-Q1'

        # Get period for date
        found_period = repo.get_period_for_date('2025-02-15')
        assert found_period is not None
        assert found_period.period_name == '2025-Q1'

        # Close period
        closed = repo.close_period(period.id, 'test_user')
        assert closed.status == 'closed'


def test_batch_upload_repository(test_db):
    """Test batch upload repository operations"""
    with test_db.session_scope() as session:
        repo = BatchUploadRepository(session)

        # Create batch
        batch_data = {
            'batch_id': 'TEST-BATCH-001',
            'filename': 'test.csv',
            'file_type': 'csv',
            'status': 'pending',
            'total_records': 10
        }

        batch = repo.create(batch_data)
        assert batch.id is not None
        assert batch.batch_id == 'TEST-BATCH-001'

        # Update status
        updated = repo.update_status(batch.id, 'processing')
        assert updated.status == 'processing'
        assert updated.started_at is not None

        # Update progress
        updated = repo.update_progress(batch.id, 5, 4, 1)
        assert updated.processed_records == 5
        assert updated.successful_records == 4


def test_vat_period_service(test_db):
    """Test VAT period service"""
    # Note: VATPerıodService uses global db_manager,
    # so this is an integration test
    service = VATPeriodService()

    # Create quarterly periods
    periods = service.create_quarterly_periods(2025)
    assert len(periods) == 4
    assert periods[0]['period_name'] == '2025-Q1'
    assert periods[3]['period_name'] == '2025-Q4'

    # Get period for date
    period = service.get_period_for_invoice_date('2025-02-15')
    assert period is not None
    assert period['period_name'] == '2025-Q1'


def test_invoice_filtering(test_db):
    """Test advanced invoice filtering"""
    with test_db.session_scope() as session:
        repo = InvoiceRepository(session)

        # Create test invoices
        invoices_data = [
            {
                'invoice_number': f'INV-{i:03d}',
                'transaction_id': f'TXN-{i:03d}',
                'amount': 100.0 * i,
                'country_code': 'DE' if i % 2 == 0 else 'FR',
                'invoice_date': f'2025-01-{(i % 28) + 1:02d}',
                'category': 'standard',
                'vat_rate': 19.0,
                'vat_amount': 19.0 * i,
                'total_amount': 119.0 * i,
                'validation_status': 'valid'
            }
            for i in range(1, 11)
        ]

        repo.create_batch(invoices_data)

        # Filter by country
        de_invoices = repo.filter(country_code='DE')
        assert len(de_invoices) == 5

        # Filter by amount range
        expensive = repo.filter(min_amount=500.0)
        assert len(expensive) > 0

        # Get summary stats
        stats = repo.get_summary_stats(country_code='DE')
        assert stats['total_count'] == 5
        assert stats['total_base_amount'] > 0


def test_search_invoices(test_db):
    """Test invoice search functionality"""
    with test_db.session_scope() as session:
        repo = InvoiceRepository(session)

        # Create invoice with customer name
        invoice_data = {
            'invoice_number': 'INV-SEARCH-001',
            'transaction_id': 'TXN-SEARCH-001',
            'amount': 100.0,
            'country_code': 'DE',
            'invoice_date': '2025-01-15',
            'category': 'standard',
            'customer_name': 'Acme Corporation',
            'vat_rate': 19.0,
            'vat_amount': 19.0,
            'total_amount': 119.0,
            'validation_status': 'valid'
        }

        repo.create(invoice_data)

        # Search by customer name
        results = repo.search('Acme')
        assert len(results) == 1
        assert results[0].customer_name == 'Acme Corporation'

        # Search by invoice number
        results = repo.search('SEARCH')
        assert len(results) == 1

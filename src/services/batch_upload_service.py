"""Batch upload processing service"""

import uuid
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from ..core.calculator import VATCalculator
from ..core.validator import DataValidator
from ..ingestion.reader import DataReader
from ..ingestion.parser import DataParser
from ..database.repositories import BatchUploadRepository, InvoiceRepository, VATPeriodRepository
from ..database.connection import get_db_manager
from ..utils.logger import get_logger
from ..utils.exceptions import DataIngestionError


logger = get_logger(__name__)


class BatchUploadService:
    """Service for processing batch file uploads"""

    def __init__(self, config: Dict[str, Any] = None):
        self.db_manager = get_db_manager()
        self.config = config or self._get_default_config()

        # Initialize components
        vat_rates_path = 'config/vat_rates.json'
        self.calculator = VATCalculator(vat_rates_path)
        self.validator = DataValidator(self.config.get('validation', {}))

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'validation': {
                'strict_mode': False,
                'required_fields': [
                    'transaction_id', 'amount', 'country_code',
                    'invoice_date', 'category'
                ],
                'rules': {
                    'amount': {'min': 0, 'max': 1000000}
                }
            }
        }

    def process_file(
        self,
        file_path: str,
        uploaded_by: str = 'system',
        auto_assign_period: bool = True
    ) -> Dict[str, Any]:
        """
        Process a batch upload file

        Args:
            file_path: Path to the file to process
            uploaded_by: User who uploaded the file
            auto_assign_period: Automatically assign invoices to VAT periods

        Returns:
            dict: Processing results including batch ID and statistics
        """
        batch_id = str(uuid.uuid4())[:8]
        filename = os.path.basename(file_path)
        file_ext = Path(file_path).suffix.lower()

        logger.info(f"Starting batch upload processing: {batch_id} - {filename}")

        # Create batch upload record
        with self.db_manager.session_scope() as session:
            batch_repo = BatchUploadRepository(session)

            batch_data = {
                'batch_id': batch_id,
                'filename': filename,
                'file_type': file_ext[1:] if file_ext else 'unknown',
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                'status': 'pending',
                'uploaded_by': uploaded_by
            }

            batch = batch_repo.create(batch_data)
            batch_db_id = batch.id  # Save ID before session closes

        try:
            # Update status to processing
            with self.db_manager.session_scope() as session:
                batch_repo = BatchUploadRepository(session)
                batch_repo.update_status(batch_db_id, 'processing')

            # Read and process file
            result = self._process_batch_file(
                file_path,
                batch_db_id,
                auto_assign_period
            )

            # Update final status
            with self.db_manager.session_scope() as session:
                batch_repo = BatchUploadRepository(session)
                batch_repo.update_status(batch_db_id, 'completed')
                batch_repo.update(batch_db_id, {
                    'total_records': result['total'],
                    'processed_records': result['processed'],
                    'successful_records': result['successful'],
                    'failed_records': result['failed']
                })

            logger.info(
                f"Batch upload {batch_id} completed: "
                f"{result['successful']}/{result['total']} successful"
            )

            return {
                'batch_id': batch_id,
                'status': 'completed',
                'statistics': result
            }

        except Exception as e:
            logger.error(f"Batch upload {batch_id} failed: {e}")

            # Update status to failed
            with self.db_manager.session_scope() as session:
                batch_repo = BatchUploadRepository(session)
                batch_repo.update_status(batch_db_id, 'failed', error_message=str(e))

            return {
                'batch_id': batch_id,
                'status': 'failed',
                'error': str(e)
            }

    def _process_batch_file(
        self,
        file_path: str,
        batch_id: int,
        auto_assign_period: bool
    ) -> Dict[str, Any]:
        """Process the batch file and save invoices"""
        # Read file
        try:
            raw_transactions = DataReader.read_file(file_path)
        except Exception as e:
            raise DataIngestionError(f"Failed to read file: {e}")

        # Parse transactions
        parsed_transactions = DataParser.parse_batch(raw_transactions)

        total = len(parsed_transactions)
        processed = 0
        successful = 0
        failed = 0
        errors = []

        invoices_to_create = []

        # Process each transaction
        for idx, transaction in enumerate(parsed_transactions):
            try:
                # Validate
                is_valid, error_msg = self.validator.validate_transaction(transaction)

                # Generate invoice number if not present
                if 'invoice_number' not in transaction or not transaction['invoice_number']:
                    transaction['invoice_number'] = f"INV-{transaction['transaction_id']}"

                # Rename date field
                if 'transaction_date' in transaction:
                    transaction['invoice_date'] = transaction.pop('transaction_date')

                if is_valid:
                    # Calculate VAT
                    vat_result = self.calculator.calculate_vat(
                        amount=transaction['amount'],
                        country_code=transaction['country_code'],
                        category=transaction.get('category', 'standard')
                    )

                    # Prepare invoice data
                    invoice_data = {
                        **transaction,
                        'vat_rate': vat_result['vat_rate'],
                        'vat_amount': vat_result['vat_amount'],
                        'total_amount': vat_result['total_amount'],
                        'validation_status': 'valid',
                        'processing_status': 'completed',
                        'batch_upload_id': batch_id
                    }

                    # Auto-assign to VAT period
                    if auto_assign_period and 'invoice_date' in invoice_data:
                        with self.db_manager.session_scope() as session:
                            period_repo = VATPeriodRepository(session)
                            period = period_repo.get_period_for_date(invoice_data['invoice_date'])
                            if period:
                                invoice_data['vat_period_id'] = period.id

                    invoices_to_create.append(invoice_data)
                    successful += 1

                else:
                    # Create invoice with error
                    invoice_data = {
                        **transaction,
                        'invoice_number': transaction.get('invoice_number', f"INV-{transaction['transaction_id']}"),
                        'invoice_date': transaction.get('invoice_date', transaction.get('transaction_date', '')),
                        'vat_rate': 0.0,
                        'vat_amount': 0.0,
                        'total_amount': transaction.get('amount', 0.0),
                        'validation_status': 'invalid',
                        'processing_status': 'failed',
                        'error_message': error_msg,
                        'batch_upload_id': batch_id
                    }
                    invoices_to_create.append(invoice_data)
                    failed += 1
                    errors.append({
                        'index': idx,
                        'transaction_id': transaction.get('transaction_id'),
                        'error': error_msg
                    })

                processed += 1

            except Exception as e:
                logger.error(f"Error processing transaction {idx}: {e}")
                failed += 1
                processed += 1
                errors.append({
                    'index': idx,
                    'transaction_id': transaction.get('transaction_id', 'unknown'),
                    'error': str(e)
                })

        # Save all invoices in batch
        if invoices_to_create:
            with self.db_manager.session_scope() as session:
                invoice_repo = InvoiceRepository(session)
                invoice_repo.create_batch(invoices_to_create)

        return {
            'total': total,
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'errors': errors[:10]  # Return first 10 errors
        }

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch upload"""
        with self.db_manager.session_scope() as session:
            batch_repo = BatchUploadRepository(session)
            batch = batch_repo.get_by_batch_id(batch_id)
            return batch.to_dict() if batch else None

    def get_all_batches(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all batch uploads"""
        with self.db_manager.session_scope() as session:
            batch_repo = BatchUploadRepository(session)
            batches = batch_repo.get_all(status=status, skip=skip, limit=limit)
            return [b.to_dict() for b in batches]

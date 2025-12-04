"""Data transformation utilities"""

from datetime import datetime
from typing import Dict, Any, List

from ..utils.logger import get_logger


logger = get_logger(__name__)


class DataTransformer:
    """Transforms and formats data for VAT pipeline"""

    def __init__(self, config: Dict = None):
        """
        Initialize data transformer

        Args:
            config: Transformer configuration
        """
        self.config = config or {}

    def transform_input(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw input data to standardized format

        Args:
            raw_data: Raw transaction data

        Returns:
            dict: Transformed data
        """
        transformed = {}

        # Normalize field names
        field_mapping = {
            'id': 'transaction_id',
            'value': 'amount',
            'country': 'country_code',
            'date': 'transaction_date',
            'type': 'category'
        }

        for raw_key, value in raw_data.items():
            standard_key = field_mapping.get(raw_key, raw_key)
            transformed[standard_key] = self._normalize_value(standard_key, value)

        return transformed

    def _normalize_value(self, field_name: str, value: Any) -> Any:
        """
        Normalize field values

        Args:
            field_name: Name of the field
            value: Field value

        Returns:
            Normalized value
        """
        if value is None:
            return value

        # Normalize country code to uppercase
        if field_name == 'country_code':
            return str(value).upper().strip()

        # Normalize category to lowercase
        if field_name == 'category':
            return str(value).lower().strip()

        # Convert amount to float
        if field_name == 'amount':
            try:
                return float(value)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert amount to float: {value}")
                return value

        # Strip whitespace from strings
        if isinstance(value, str):
            return value.strip()

        return value

    def enrich_transaction(
        self,
        transaction: Dict[str, Any],
        vat_result: Dict[str, float],
        validation_status: str
    ) -> Dict[str, Any]:
        """
        Enrich transaction with calculated VAT and metadata

        Args:
            transaction: Original transaction data
            vat_result: VAT calculation result
            validation_status: Validation status

        Returns:
            dict: Enriched transaction data
        """
        enriched = transaction.copy()

        # Add VAT calculation results
        enriched.update({
            'vat_rate': vat_result['vat_rate'],
            'vat_amount': vat_result['vat_amount'],
            'total_amount': vat_result['total_amount'],
            'validation_status': validation_status,
            'processed_timestamp': datetime.now().isoformat()
        })

        return enriched

    def format_output(
        self,
        transactions: List[Dict[str, Any]],
        output_config: Dict
    ) -> List[Dict[str, Any]]:
        """
        Format transactions for output

        Args:
            transactions: List of processed transactions
            output_config: Output configuration

        Returns:
            list: Formatted transactions
        """
        output_columns = output_config.get('columns', [])
        formatted = []

        for transaction in transactions:
            if output_columns:
                # Include only specified columns
                formatted_record = {
                    col: transaction.get(col)
                    for col in output_columns
                }
            else:
                formatted_record = transaction

            formatted.append(formatted_record)

        return formatted

    def create_summary_report(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create summary report for processed transactions

        Args:
            transactions: List of processed transactions

        Returns:
            dict: Summary statistics
        """
        if not transactions:
            return {
                'total_transactions': 0,
                'total_base_amount': 0.0,
                'total_vat_amount': 0.0,
                'total_amount': 0.0,
                'by_country': {},
                'by_category': {}
            }

        total_base = sum(t.get('amount', 0) for t in transactions)
        total_vat = sum(t.get('vat_amount', 0) for t in transactions)
        total_amount = sum(t.get('total_amount', 0) for t in transactions)

        # Group by country
        by_country = {}
        for t in transactions:
            country = t.get('country_code', 'UNKNOWN')
            if country not in by_country:
                by_country[country] = {
                    'count': 0,
                    'total_base': 0.0,
                    'total_vat': 0.0
                }
            by_country[country]['count'] += 1
            by_country[country]['total_base'] += t.get('amount', 0)
            by_country[country]['total_vat'] += t.get('vat_amount', 0)

        # Group by category
        by_category = {}
        for t in transactions:
            category = t.get('category', 'unknown')
            if category not in by_category:
                by_category[category] = {
                    'count': 0,
                    'total_base': 0.0,
                    'total_vat': 0.0
                }
            by_category[category]['count'] += 1
            by_category[category]['total_base'] += t.get('amount', 0)
            by_category[category]['total_vat'] += t.get('vat_amount', 0)

        return {
            'total_transactions': len(transactions),
            'total_base_amount': round(total_base, 2),
            'total_vat_amount': round(total_vat, 2),
            'total_amount': round(total_amount, 2),
            'by_country': by_country,
            'by_category': by_category
        }

"""Data parsers and normalizers"""

from typing import Dict, Any, List
from datetime import datetime

from ..utils.logger import get_logger


logger = get_logger(__name__)


class DataParser:
    """Parses and normalizes transaction data"""

    @staticmethod
    def parse_transaction(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and normalize a single transaction

        Args:
            raw_data: Raw transaction data

        Returns:
            dict: Parsed transaction
        """
        parsed = {}

        # Transaction ID
        parsed['transaction_id'] = str(raw_data.get('transaction_id', raw_data.get('id', '')))

        # Amount - convert to float
        amount_raw = raw_data.get('amount', raw_data.get('value', 0))
        try:
            parsed['amount'] = float(amount_raw)
        except (ValueError, TypeError):
            logger.warning(f"Invalid amount value: {amount_raw}, using 0.0")
            parsed['amount'] = 0.0

        # Country code - uppercase
        country = raw_data.get('country_code', raw_data.get('country', ''))
        parsed['country_code'] = str(country).upper().strip()

        # Transaction date - normalize format
        date_raw = raw_data.get('transaction_date', raw_data.get('date', ''))
        parsed['transaction_date'] = DataParser._parse_date(date_raw)

        # Category - lowercase
        category = raw_data.get('category', raw_data.get('type', 'standard'))
        parsed['category'] = str(category).lower().strip()

        return parsed

    @staticmethod
    def _parse_date(date_value: Any) -> str:
        """
        Parse date to standardized format (YYYY-MM-DD)

        Args:
            date_value: Date value in various formats

        Returns:
            str: Standardized date string
        """
        if not date_value:
            return datetime.now().strftime('%Y-%m-%d')

        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%m-%d-%Y'
        ]

        for fmt in date_formats:
            try:
                dt = datetime.strptime(str(date_value), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If all parsing fails, log warning and return current date
        logger.warning(f"Could not parse date: {date_value}, using current date")
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def parse_batch(raw_transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse a batch of transactions

        Args:
            raw_transactions: List of raw transaction dictionaries

        Returns:
            list: List of parsed transactions
        """
        parsed_transactions = []

        for idx, raw_data in enumerate(raw_transactions):
            try:
                parsed = DataParser.parse_transaction(raw_data)
                parsed_transactions.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing transaction at index {idx}: {e}")
                # Continue processing other transactions

        logger.info(
            f"Parsed {len(parsed_transactions)}/{len(raw_transactions)} transactions"
        )

        return parsed_transactions

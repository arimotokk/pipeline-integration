"""Data validation for VAT pipeline"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import re

from ..utils.exceptions import ValidationError
from ..utils.logger import get_logger


logger = get_logger(__name__)


class DataValidator:
    """Validates transaction data for VAT processing"""

    def __init__(self, config: Dict):
        """
        Initialize validator with configuration

        Args:
            config: Validation configuration dictionary
        """
        self.config = config
        self.required_fields = config.get('required_fields', [])
        self.rules = config.get('rules', {})
        self.strict_mode = config.get('strict_mode', True)

    def validate_transaction(self, transaction: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a single transaction record

        Args:
            transaction: Transaction data dictionary

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check required fields
            missing_fields = self._check_required_fields(transaction)
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                if self.strict_mode:
                    return False, error_msg
                logger.warning(error_msg)

            # Validate individual fields
            for field_name, field_rules in self.rules.items():
                if field_name in transaction:
                    is_valid, error_msg = self._validate_field(
                        field_name,
                        transaction[field_name],
                        field_rules
                    )
                    if not is_valid:
                        if self.strict_mode:
                            return False, error_msg
                        logger.warning(error_msg)

            return True, None

        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _check_required_fields(self, transaction: Dict[str, Any]) -> List[str]:
        """Check for missing required fields"""
        missing = []
        for field in self.required_fields:
            if field not in transaction or transaction[field] is None:
                missing.append(field)
        return missing

    def _validate_field(
        self,
        field_name: str,
        value: Any,
        rules: Dict
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a field against its rules

        Args:
            field_name: Name of the field
            value: Field value
            rules: Validation rules for the field

        Returns:
            tuple: (is_valid, error_message)
        """
        # Type validation
        if 'type' in rules:
            if not self._validate_type(value, rules['type']):
                return False, f"{field_name}: Invalid type, expected {rules['type']}"

        # Min/max validation for numeric fields
        if 'min' in rules:
            try:
                if float(value) < rules['min']:
                    return False, f"{field_name}: Value {value} is below minimum {rules['min']}"
            except (ValueError, TypeError):
                return False, f"{field_name}: Cannot validate min for non-numeric value"

        if 'max' in rules:
            try:
                if float(value) > rules['max']:
                    return False, f"{field_name}: Value {value} exceeds maximum {rules['max']}"
            except (ValueError, TypeError):
                return False, f"{field_name}: Cannot validate max for non-numeric value"

        # Length validation for strings
        if 'length' in rules:
            if len(str(value)) != rules['length']:
                return False, f"{field_name}: Invalid length, expected {rules['length']}"

        # Pattern validation
        if 'pattern' in rules:
            if not re.match(rules['pattern'], str(value)):
                return False, f"{field_name}: Does not match required pattern"

        # Date format validation
        if 'format' in rules and field_name == 'transaction_date':
            if not self._validate_date(value, rules['format']):
                return False, f"{field_name}: Invalid date format, expected {rules['format']}"

        return True, None

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        type_map = {
            'string': str,
            'int': int,
            'float': (int, float),
            'bool': bool
        }

        expected = type_map.get(expected_type)
        if expected is None:
            return True

        return isinstance(value, expected)

    def _validate_date(self, value: str, date_format: str) -> bool:
        """Validate date string format"""
        try:
            datetime.strptime(str(value), date_format)
            return True
        except (ValueError, TypeError):
            return False

    def validate_batch(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of transactions

        Args:
            transactions: List of transaction dictionaries

        Returns:
            dict: Validation results with statistics
        """
        results = {
            'total': len(transactions),
            'valid': 0,
            'invalid': 0,
            'errors': []
        }

        for idx, transaction in enumerate(transactions):
            is_valid, error_msg = self.validate_transaction(transaction)
            if is_valid:
                results['valid'] += 1
            else:
                results['invalid'] += 1
                results['errors'].append({
                    'index': idx,
                    'transaction_id': transaction.get('transaction_id', 'unknown'),
                    'error': error_msg
                })

        logger.info(
            f"Batch validation complete: {results['valid']}/{results['total']} valid, "
            f"{results['invalid']} invalid"
        )

        return results

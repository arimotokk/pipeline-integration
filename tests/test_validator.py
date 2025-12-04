"""Tests for data validator"""

import pytest
from src.core.validator import DataValidator


@pytest.fixture
def validator_config():
    """Create validator configuration"""
    return {
        'strict_mode': True,
        'required_fields': [
            'transaction_id',
            'amount',
            'country_code',
            'transaction_date',
            'category'
        ],
        'rules': {
            'amount': {
                'min': 0,
                'max': 1000000
            },
            'country_code': {
                'type': 'string',
                'length': 2
            }
        }
    }


def test_validator_initialization(validator_config):
    """Test validator initialization"""
    validator = DataValidator(validator_config)
    assert validator is not None
    assert validator.strict_mode is True


def test_validate_valid_transaction(validator_config):
    """Test validation of valid transaction"""
    validator = DataValidator(validator_config)

    transaction = {
        'transaction_id': 'TXN001',
        'amount': 100.0,
        'country_code': 'DE',
        'transaction_date': '2025-01-01',
        'category': 'standard'
    }

    is_valid, error = validator.validate_transaction(transaction)
    assert is_valid is True
    assert error is None


def test_validate_missing_required_field(validator_config):
    """Test validation with missing required field"""
    validator = DataValidator(validator_config)

    transaction = {
        'transaction_id': 'TXN001',
        'amount': 100.0,
        'country_code': 'DE'
        # Missing transaction_date and category
    }

    is_valid, error = validator.validate_transaction(transaction)
    assert is_valid is False
    assert 'Missing required fields' in error


def test_validate_amount_below_minimum(validator_config):
    """Test validation with amount below minimum"""
    validator = DataValidator(validator_config)

    transaction = {
        'transaction_id': 'TXN001',
        'amount': -10.0,
        'country_code': 'DE',
        'transaction_date': '2025-01-01',
        'category': 'standard'
    }

    is_valid, error = validator.validate_transaction(transaction)
    assert is_valid is False
    assert 'below minimum' in error


def test_validate_invalid_country_code_length(validator_config):
    """Test validation with invalid country code length"""
    validator = DataValidator(validator_config)

    transaction = {
        'transaction_id': 'TXN001',
        'amount': 100.0,
        'country_code': 'DEU',  # Should be 2 characters
        'transaction_date': '2025-01-01',
        'category': 'standard'
    }

    is_valid, error = validator.validate_transaction(transaction)
    assert is_valid is False
    assert 'Invalid length' in error


def test_validate_batch(validator_config):
    """Test batch validation"""
    validator = DataValidator(validator_config)

    transactions = [
        {
            'transaction_id': 'TXN001',
            'amount': 100.0,
            'country_code': 'DE',
            'transaction_date': '2025-01-01',
            'category': 'standard'
        },
        {
            'transaction_id': 'TXN002',
            'amount': -10.0,  # Invalid
            'country_code': 'FR',
            'transaction_date': '2025-01-01',
            'category': 'food'
        }
    ]

    results = validator.validate_batch(transactions)
    assert results['total'] == 2
    assert results['valid'] == 1
    assert results['invalid'] == 1

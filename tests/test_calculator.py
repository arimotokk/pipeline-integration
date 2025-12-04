"""Tests for VAT calculator"""

import pytest
import json
import tempfile
from src.core.calculator import VATCalculator
from src.utils.exceptions import CountryNotSupportedError, CalculationError


@pytest.fixture
def vat_rates_file():
    """Create temporary VAT rates configuration file"""
    rates_config = {
        "rates": {
            "DE": {
                "country": "Germany",
                "standard_rate": 19.0,
                "categories": {
                    "standard": 19.0,
                    "food": 7.0
                }
            },
            "FR": {
                "country": "France",
                "standard_rate": 20.0,
                "categories": {
                    "standard": 20.0,
                    "food": 5.5
                }
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(rates_config, f)
        return f.name


def test_calculator_initialization(vat_rates_file):
    """Test calculator initialization"""
    calculator = VATCalculator(vat_rates_file)
    assert calculator is not None
    assert len(calculator.rates) == 2


def test_get_vat_rate(vat_rates_file):
    """Test getting VAT rate for country and category"""
    calculator = VATCalculator(vat_rates_file)

    # Standard rate
    rate = calculator.get_vat_rate('DE', 'standard')
    assert rate == 19.0

    # Reduced rate
    rate = calculator.get_vat_rate('DE', 'food')
    assert rate == 7.0


def test_get_vat_rate_unsupported_country(vat_rates_file):
    """Test error handling for unsupported country"""
    calculator = VATCalculator(vat_rates_file)

    with pytest.raises(CountryNotSupportedError):
        calculator.get_vat_rate('XX', 'standard')


def test_calculate_vat(vat_rates_file):
    """Test VAT calculation"""
    calculator = VATCalculator(vat_rates_file)

    result = calculator.calculate_vat(100.0, 'DE', 'standard')

    assert result['vat_rate'] == 19.0
    assert result['vat_amount'] == 19.0
    assert result['total_amount'] == 119.0


def test_calculate_vat_with_decimals(vat_rates_file):
    """Test VAT calculation with decimal amounts"""
    calculator = VATCalculator(vat_rates_file)

    result = calculator.calculate_vat(99.99, 'FR', 'food')

    assert result['vat_rate'] == 5.5
    assert result['vat_amount'] == 5.50  # Rounded
    assert result['total_amount'] == 105.49


def test_get_supported_countries(vat_rates_file):
    """Test getting list of supported countries"""
    calculator = VATCalculator(vat_rates_file)

    countries = calculator.get_supported_countries()
    assert 'DE' in countries
    assert 'FR' in countries
    assert len(countries) == 2

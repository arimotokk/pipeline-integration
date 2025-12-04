"""VAT calculation engine"""

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from ..utils.exceptions import (
    CalculationError,
    CountryNotSupportedError,
    InvalidCategoryError,
    ConfigurationError
)
from ..utils.logger import get_logger


logger = get_logger(__name__)


class VATCalculator:
    """Handles VAT calculations based on configured rates"""

    def __init__(self, rates_config_path: str):
        """
        Initialize VAT calculator with rates configuration

        Args:
            rates_config_path: Path to VAT rates JSON configuration file
        """
        self.rates_config_path = rates_config_path
        self.rates = self._load_rates()
        logger.info(f"Loaded VAT rates for {len(self.rates)} countries")

    def _load_rates(self) -> Dict:
        """Load VAT rates from configuration file"""
        try:
            with open(self.rates_config_path, 'r') as f:
                config = json.load(f)
                return config.get('rates', {})
        except FileNotFoundError:
            raise ConfigurationError(
                f"VAT rates configuration file not found: {self.rates_config_path}"
            )
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in VAT rates configuration: {e}"
            )

    def get_vat_rate(self, country_code: str, category: str = 'standard') -> float:
        """
        Get VAT rate for a country and category

        Args:
            country_code: ISO country code (e.g., 'DE', 'FR')
            category: Product/service category

        Returns:
            float: VAT rate as percentage

        Raises:
            CountryNotSupportedError: If country is not configured
            InvalidCategoryError: If category is not found for country
        """
        country_code = country_code.upper()

        if country_code not in self.rates:
            raise CountryNotSupportedError(
                f"VAT rates not configured for country: {country_code}"
            )

        country_config = self.rates[country_code]
        categories = country_config.get('categories', {})

        if category not in categories:
            logger.warning(
                f"Category '{category}' not found for {country_code}, "
                f"using standard rate"
            )
            category = 'standard'

        return categories.get(category, country_config.get('standard_rate', 0.0))

    def calculate_vat(
        self,
        amount: float,
        country_code: str,
        category: str = 'standard'
    ) -> Dict[str, float]:
        """
        Calculate VAT amount and total

        Args:
            amount: Base amount (excluding VAT)
            country_code: ISO country code
            category: Product/service category

        Returns:
            dict: Contains vat_rate, vat_amount, and total_amount

        Raises:
            CalculationError: If calculation fails
        """
        try:
            # Convert to Decimal for precise monetary calculations
            amount_decimal = Decimal(str(amount))

            # Get VAT rate
            vat_rate = self.get_vat_rate(country_code, category)
            vat_rate_decimal = Decimal(str(vat_rate))

            # Calculate VAT amount
            vat_amount = (amount_decimal * vat_rate_decimal / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

            # Calculate total
            total_amount = amount_decimal + vat_amount

            result = {
                'vat_rate': float(vat_rate),
                'vat_amount': float(vat_amount),
                'total_amount': float(total_amount)
            }

            logger.debug(
                f"Calculated VAT for {country_code}/{category}: "
                f"amount={amount}, vat={result['vat_amount']}, "
                f"total={result['total_amount']}"
            )

            return result

        except (ValueError, TypeError) as e:
            raise CalculationError(f"Invalid amount for VAT calculation: {e}")

    def get_supported_countries(self) -> list:
        """Get list of supported country codes"""
        return list(self.rates.keys())

    def get_categories_for_country(self, country_code: str) -> list:
        """Get available categories for a country"""
        country_code = country_code.upper()
        if country_code not in self.rates:
            return []
        return list(self.rates[country_code].get('categories', {}).keys())

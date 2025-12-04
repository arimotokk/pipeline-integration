"""Custom exceptions for VAT pipeline"""


class VATError(Exception):
    """Base exception for VAT pipeline errors"""
    pass


class ValidationError(VATError):
    """Raised when data validation fails"""
    pass


class CalculationError(VATError):
    """Raised when VAT calculation fails"""
    pass


class ConfigurationError(VATError):
    """Raised when configuration is invalid"""
    pass


class DataIngestionError(VATError):
    """Raised when data ingestion fails"""
    pass


class CountryNotSupportedError(VATError):
    """Raised when country VAT rates are not configured"""
    pass


class InvalidCategoryError(VATError):
    """Raised when product category is not recognized"""
    pass

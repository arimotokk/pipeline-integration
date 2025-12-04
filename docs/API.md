# VAT Integration Pipeline - API Documentation

## Overview
This document provides detailed API documentation for the VAT Integration Pipeline Phase 1 components.

## Core Modules

### VATCalculator

Located in `src/core/calculator.py`

#### Initialization
```python
from src.core.calculator import VATCalculator

calculator = VATCalculator(rates_config_path='config/vat_rates.json')
```

#### Methods

##### `get_vat_rate(country_code: str, category: str = 'standard') -> float`
Get VAT rate for a country and category.

**Parameters:**
- `country_code` (str): ISO country code (e.g., 'DE', 'FR')
- `category` (str): Product/service category (default: 'standard')

**Returns:**
- `float`: VAT rate as percentage

**Raises:**
- `CountryNotSupportedError`: If country is not configured
- `InvalidCategoryError`: If category is not found

**Example:**
```python
rate = calculator.get_vat_rate('DE', 'food')
# Returns: 7.0
```

##### `calculate_vat(amount: float, country_code: str, category: str = 'standard') -> Dict[str, float]`
Calculate VAT amount and total.

**Parameters:**
- `amount` (float): Base amount excluding VAT
- `country_code` (str): ISO country code
- `category` (str): Product/service category

**Returns:**
- `dict`: Contains `vat_rate`, `vat_amount`, and `total_amount`

**Example:**
```python
result = calculator.calculate_vat(100.0, 'DE', 'standard')
# Returns: {'vat_rate': 19.0, 'vat_amount': 19.0, 'total_amount': 119.0}
```

### DataValidator

Located in `src/core/validator.py`

#### Initialization
```python
from src.core.validator import DataValidator

config = {
    'strict_mode': True,
    'required_fields': ['transaction_id', 'amount', 'country_code'],
    'rules': {
        'amount': {'min': 0, 'max': 1000000}
    }
}
validator = DataValidator(config)
```

#### Methods

##### `validate_transaction(transaction: Dict[str, Any]) -> tuple[bool, Optional[str]]`
Validate a single transaction.

**Parameters:**
- `transaction` (dict): Transaction data

**Returns:**
- `tuple`: (is_valid, error_message)

**Example:**
```python
transaction = {
    'transaction_id': 'TXN001',
    'amount': 100.0,
    'country_code': 'DE'
}
is_valid, error = validator.validate_transaction(transaction)
```

##### `validate_batch(transactions: List[Dict[str, Any]]) -> Dict[str, Any]`
Validate a batch of transactions.

**Returns:**
- `dict`: Validation results with statistics

### DataTransformer

Located in `src/core/transformer.py`

#### Methods

##### `transform_input(raw_data: Dict[str, Any]) -> Dict[str, Any]`
Transform raw input to standardized format.

##### `enrich_transaction(transaction: Dict, vat_result: Dict, validation_status: str) -> Dict`
Enrich transaction with VAT and metadata.

##### `create_summary_report(transactions: List[Dict]) -> Dict[str, Any]`
Create summary statistics.

## Data Ingestion

### DataReader

Located in `src/ingestion/reader.py`

#### Static Methods

##### `read_csv(file_path: str) -> List[Dict[str, Any]]`
Read transactions from CSV file.

##### `read_json(file_path: str) -> List[Dict[str, Any]]`
Read transactions from JSON file.

##### `read_file(file_path: str) -> List[Dict[str, Any]]`
Auto-detect format and read file.

### DataParser

Located in `src/ingestion/parser.py`

#### Static Methods

##### `parse_transaction(raw_data: Dict[str, Any]) -> Dict[str, Any]`
Parse and normalize a single transaction.

##### `parse_batch(raw_transactions: List[Dict]) -> List[Dict]`
Parse a batch of transactions.

## Pipeline

### VATPipeline

Located in `src/pipeline/runner.py`

#### Initialization
```python
from src.pipeline.runner import VATPipeline

pipeline = VATPipeline(config_path='config/pipeline.yaml')
```

#### Methods

##### `process(input_path: str, output_dir: str) -> Dict[str, Any]`
Process transactions through the pipeline.

**Parameters:**
- `input_path` (str): Path to input file
- `output_dir` (str): Directory for output files

**Returns:**
- `dict`: Processing results and statistics

**Example:**
```python
results = pipeline.process(
    input_path='data/input/transactions.csv',
    output_dir='data/output/'
)
```

## Exceptions

Located in `src/utils/exceptions.py`

- `VATError`: Base exception
- `ValidationError`: Data validation failures
- `CalculationError`: VAT calculation failures
- `ConfigurationError`: Invalid configuration
- `DataIngestionError`: Data ingestion failures
- `CountryNotSupportedError`: Unsupported country
- `InvalidCategoryError`: Unrecognized category

## Logging

Located in `src/utils/logger.py`

### Functions

##### `setup_logger(name: str, log_file: str = None, level: int = logging.INFO) -> logging.Logger`
Set up a logger with console and file output.

##### `get_logger(name: str) -> logging.Logger`
Get or create a logger instance.

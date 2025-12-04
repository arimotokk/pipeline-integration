# Configuration Guide

## Overview
The VAT Integration Pipeline uses two main configuration files:
1. `config/vat_rates.json` - VAT rates by country
2. `config/pipeline.yaml` - Pipeline behavior settings

## VAT Rates Configuration

### File: `config/vat_rates.json`

Structure:
```json
{
  "version": "1.0.0",
  "last_updated": "2025-01-01",
  "rates": {
    "COUNTRY_CODE": {
      "country": "Country Name",
      "standard_rate": 20.0,
      "reduced_rates": [5.0, 10.0],
      "categories": {
        "standard": 20.0,
        "food": 5.0,
        "books": 5.0,
        "medical": 10.0,
        "transport": 10.0
      }
    }
  }
}
```

### Adding a New Country

1. Add new entry in the `rates` object
2. Use ISO 3166-1 alpha-2 country code (2 letters)
3. Specify standard rate and categories
4. Update the `last_updated` field

Example:
```json
"SE": {
  "country": "Sweden",
  "standard_rate": 25.0,
  "reduced_rates": [6.0, 12.0],
  "categories": {
    "standard": 25.0,
    "food": 12.0,
    "books": 6.0,
    "medical": 6.0,
    "transport": 6.0
  }
}
```

### Supported Categories

- `standard`: Default VAT rate
- `food`: Food and beverages
- `books`: Books and publications
- `medical`: Medical supplies and services
- `transport`: Transportation services

You can add custom categories as needed.

## Pipeline Configuration

### File: `config/pipeline.yaml`

### Processing Settings

```yaml
processing:
  batch_size: 1000          # Number of records to process per batch
  max_retries: 3            # Maximum retry attempts for failed operations
  timeout_seconds: 300      # Timeout for pipeline execution
```

### Validation Settings

```yaml
validation:
  strict_mode: true         # Fail on validation errors if true
  required_fields:          # List of required fields
    - transaction_id
    - amount
    - country_code
    - transaction_date
    - category

  rules:
    amount:
      min: 0                # Minimum amount
      max: 1000000          # Maximum amount
    country_code:
      type: "string"
      length: 2             # ISO country code length
    transaction_date:
      format: "%Y-%m-%d"    # Date format
```

#### Validation Rules

**Field Types:**
- `string`: Text field
- `int`: Integer number
- `float`: Decimal number
- `bool`: Boolean value

**Numeric Rules:**
- `min`: Minimum value (inclusive)
- `max`: Maximum value (inclusive)

**String Rules:**
- `length`: Expected string length
- `pattern`: Regex pattern to match

**Date Rules:**
- `format`: Expected date format (Python strftime format)

### Output Settings

```yaml
output:
  format: "csv"                    # Output format (csv or json)
  include_timestamp: true          # Add timestamp to filename
  file_prefix: "vat_processed"     # Output file prefix
  columns:                         # Columns to include in output
    - transaction_id
    - amount
    - country_code
    - vat_rate
    - vat_amount
    - total_amount
    - validation_status
    - processed_timestamp
```

### Logging Settings

```yaml
logging:
  level: "INFO"                    # Log level: DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  output: "logs/pipeline.log"      # Log file path
```

### Error Handling

```yaml
error_handling:
  on_validation_error: "log_and_skip"    # Action on validation error
  on_calculation_error: "log_and_skip"   # Action on calculation error
  create_error_report: true              # Generate error report
  error_report_path: "data/output/errors"
```

**Error Handling Options:**
- `log_and_skip`: Log error and continue processing
- `fail`: Stop pipeline execution
- `log_and_continue`: Log error but mark as processed

## Environment Variables

You can override configuration values using environment variables:

```bash
export VAT_CONFIG_PATH=/path/to/config/pipeline.yaml
export VAT_RATES_PATH=/path/to/config/vat_rates.json
export VAT_LOG_LEVEL=DEBUG
```

## Best Practices

1. **Version Control**: Keep configuration files in version control
2. **Validation**: Validate configuration changes before deployment
3. **Documentation**: Document any custom categories or rules
4. **Testing**: Test configuration with sample data
5. **Backup**: Keep backups of VAT rates before updates
6. **Auditing**: Track changes to VAT rates with timestamps

## Configuration Validation

You can validate your configuration by running:

```bash
python -m src.pipeline.runner --input data/input/sample_transactions.csv --output data/output/ --config config/pipeline.yaml
```

If the configuration is invalid, the pipeline will report errors during initialization.

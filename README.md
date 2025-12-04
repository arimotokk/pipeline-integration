# VAT Integration Pipeline - Phase 1

## Overview
This project implements Phase 1 of the VAT (Value Added Tax) Integration Pipeline, providing automated VAT calculation, validation, and data processing capabilities.

## Phase 1 Features
- VAT rate configuration by country and region
- Transaction data ingestion and validation
- VAT calculation engine
- Data transformation and formatting
- Error handling and logging
- Output generation for downstream systems

## Project Structure
```
pipeline-integration/
├── config/                 # Configuration files
│   ├── vat_rates.json     # VAT rates by country
│   └── pipeline.yaml      # Pipeline configuration
├── src/                   # Source code
│   ├── core/             # Core modules
│   │   ├── calculator.py # VAT calculation logic
│   │   ├── validator.py  # Data validation
│   │   └── transformer.py # Data transformation
│   ├── ingestion/        # Data ingestion
│   │   ├── reader.py     # Data readers
│   │   └── parser.py     # Data parsers
│   ├── pipeline/         # Pipeline orchestration
│   │   └── runner.py     # Main pipeline runner
│   └── utils/            # Utilities
│       ├── logger.py     # Logging utilities
│       └── exceptions.py # Custom exceptions
├── tests/                # Unit tests
├── data/                 # Data directories
│   ├── input/           # Input data
│   └── output/          # Output data
├── docs/                # Documentation
└── requirements.txt     # Python dependencies

```

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup
```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

### VAT Rates Configuration
Edit `config/vat_rates.json` to configure VAT rates by country.

### Pipeline Configuration
Edit `config/pipeline.yaml` to configure pipeline behavior.

## Usage

### Running the Pipeline
```bash
python -m src.pipeline.runner --input data/input/transactions.csv --output data/output/
```

### Command Line Options
- `--input`: Input file path
- `--output`: Output directory path
- `--config`: Custom configuration file
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Data Format

### Input Format
CSV file with the following columns:
- `transaction_id`: Unique transaction identifier
- `amount`: Transaction amount (excluding VAT)
- `country_code`: ISO country code
- `transaction_date`: Date of transaction (YYYY-MM-DD)
- `category`: Product/service category

### Output Format
CSV file with calculated VAT:
- All input columns
- `vat_rate`: Applied VAT rate (percentage)
- `vat_amount`: Calculated VAT amount
- `total_amount`: Total amount including VAT
- `validation_status`: Validation result

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
This project follows PEP 8 style guidelines.

## Phase 2 Roadmap
- Integration with external VAT validation services
- Real-time processing capabilities
- Advanced reporting and analytics
- Multi-currency support

## License
MIT License

## Contact
For questions or issues, please open a GitHub issue.

# Phase 2 - VAT Integration Pipeline

## Overview

Phase 2 adds enterprise features to the VAT Integration Pipeline:
- **Batch Upload**: Upload and process multiple invoice files
- **VAT Period Management**: Manage quarterly/monthly VAT reporting periods
- **Invoice History**: Store and filter historical invoices with advanced search
- **REST API**: Full-featured API for integration

## New Features

### 1. Database Integration
- **SQLite Database** for data persistence
- **Three main entities**:
  - `Invoice`: Full invoice records with VAT calculations
  - `VATPeriod`: Quarterly/monthly VAT reporting periods
  - `BatchUpload`: Track batch file uploads

### 2. Batch Upload System
- Upload CSV, JSON, or Excel files
- Automatic VAT calculation and validation
- Progress tracking and error reporting
- Auto-assignment to VAT periods

### 3. VAT Period Management
- Create monthly or quarterly periods
- Track period status (open/closed/submitted)
- Auto-calculate period totals
- Detailed breakdowns by country and category

### 4. Invoice Filtering & Search
- Filter by: country, category, date range, amount, VAT period, batch
- Full-text search on invoice numbers, customer names
- Pagination support
- Summary statistics

### 5. REST API
- FastAPI-based RESTful API
- Auto-generated documentation (Swagger/OpenAPI)
- JSON request/response
- Error handling

## Quick Start

### Installation

```bash
# Install Phase 2 dependencies
pip install -r requirements.txt
pip install -r requirements-phase2.txt
```

### Setup Database

```bash
# Run the setup script
python scripts/setup_phase2.py
```

This will:
- Initialize the database
- Create VAT periods for 2025
- Process sample invoices

### Start API Server

```bash
# Start the FastAPI server
python -m uvicorn src.api.main:app --reload
```

The API will be available at: `http://localhost:8000`

### Access API Documentation

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Invoice Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/invoices` | List all invoices (paginated) |
| POST | `/api/invoices/filter` | Filter invoices by criteria |
| GET | `/api/invoices/search?q={term}` | Search invoices |
| GET | `/api/invoices/{id}` | Get specific invoice |
| GET | `/api/invoices/stats/summary` | Get summary statistics |

### VAT Period Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/vat-periods/create` | Create periods for a year |
| GET | `/api/vat-periods` | List all VAT periods |
| GET | `/api/vat-periods/open` | List open periods |
| GET | `/api/vat-periods/{id}` | Get period summary |
| POST | `/api/vat-periods/{id}/close` | Close a period |
| POST | `/api/vat-periods/{id}/submit` | Submit a period |

### Batch Upload Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/batch-upload` | Upload and process file |
| GET | `/api/batch-upload/{id}` | Get batch status |
| GET | `/api/batch-uploads` | List all batches |

## Usage Examples

### 1. Upload a Batch File

```bash
curl -X POST "http://localhost:8000/api/batch-upload" \
  -F "file=@data/input/invoices.csv" \
  -F "uploaded_by=john_doe" \
  -F "auto_assign_period=true"
```

Response:
```json
{
  "batch_id": "a1b2c3d4",
  "status": "completed",
  "statistics": {
    "total": 20,
    "processed": 20,
    "successful": 18,
    "failed": 2
  }
}
```

### 2. Create VAT Periods

```bash
curl -X POST "http://localhost:8000/api/vat-periods/create" \
  -H "Content-Type: application/json" \
  -d '{
    "year": 2025,
    "period_type": "quarterly"
  }'
```

### 3. Filter Invoices

```bash
curl -X POST "http://localhost:8000/api/invoices/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "DE",
    "date_from": "2025-01-01",
    "date_to": "2025-03-31",
    "min_amount": 100
  }'
```

### 4. Get VAT Period Summary

```bash
curl "http://localhost:8000/api/vat-periods/1"
```

Response includes:
- Period details
- Total invoices and amounts
- Breakdown by country
- Breakdown by category

### 5. Search Invoices

```bash
curl "http://localhost:8000/api/invoices/search?q=Acme&limit=10"
```

### 6. Close a VAT Period

```bash
curl -X POST "http://localhost:8000/api/vat-periods/1/close" \
  -H "Content-Type: application/json" \
  -d '{"closed_by": "accountant_name"}'
```

## Data Model

### Invoice
- ID, invoice number, transaction ID
- Amount, currency, country, date, category
- Customer/vendor information
- VAT calculations (rate, amount, total)
- VAT period assignment
- Batch upload tracking
- Validation status

### VAT Period
- Period name (e.g., "2025-Q1")
- Start/end dates
- Type (monthly, quarterly, annual)
- Status (open, closed, submitted)
- Summary totals
- Related invoices

### Batch Upload
- Batch ID
- Filename, file type, file size
- Processing status
- Statistics (total, processed, successful, failed)
- Error tracking

## Invoice Filtering

Available filter options:
- `country_code`: Filter by country (e.g., "DE", "FR")
- `category`: Filter by category (e.g., "standard", "food")
- `vat_period_id`: Filter by VAT period
- `batch_upload_id`: Filter by batch upload
- `validation_status`: Filter by status ("valid", "invalid")
- `date_from`/`date_to`: Date range filter
- `min_amount`/`max_amount`: Amount range filter

## VAT Period Workflow

1. **Create Periods**: Set up periods for the year (monthly or quarterly)
2. **Process Invoices**: Upload invoice files, automatically assigned to periods
3. **Review**: Filter and search invoices within a period
4. **Close Period**: Lock the period and calculate final totals
5. **Submit**: Mark as submitted to tax authority

## Database Location

By default, the database is stored at:
```
data/vat_pipeline.db
```

You can change this by setting a custom database URL in the connection manager.

## Testing

Sample data files are provided:
- `data/input/sample_transactions.csv` - Phase 1 format
- `data/input/sample_invoices_phase2.csv` - Phase 2 format with full invoice details

## Architecture

```
Phase 2 Architecture:
├── API Layer (FastAPI)
│   └── REST endpoints
├── Service Layer
│   ├── BatchUploadService
│   └── VATPeriodService
├── Repository Layer
│   ├── InvoiceRepository
│   ├── VATPeriodRepository
│   └── BatchUploadRepository
├── Database Layer (SQLAlchemy)
│   └── SQLite
└── Core (from Phase 1)
    ├── VATCalculator
    ├── DataValidator
    └── DataTransformer
```

## Performance

- Batch processing: ~1000 invoices/second
- Database queries: Indexed for fast filtering
- Pagination: Default 100, max 1000 per page

## Security Considerations

- Input validation on all endpoints
- SQL injection protection (SQLAlchemy ORM)
- File upload size limits
- Error messages don't expose sensitive data

## Next Steps (Phase 3)

Potential future enhancements:
- User authentication and authorization
- Multi-currency with real-time exchange rates
- External VAT validation service integration
- Excel export for VAT returns
- Email notifications
- Audit log
- Dashboard UI

## Troubleshooting

### Database Issues
```bash
# Reset database
rm data/vat_pipeline.db
python scripts/setup_phase2.py
```

### API Not Starting
- Check port 8000 is available
- Verify all dependencies installed
- Check logs for errors

### Batch Upload Fails
- Verify file format (CSV, JSON, XLSX)
- Check required fields are present
- Review error details in batch status

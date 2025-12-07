#!/usr/bin/env python
"""
Setup script for Phase 2
- Initialize database
- Create VAT periods for 2025
- Process sample invoices
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.connection import get_db_manager
from src.services.vat_period_service import VATPeriodService
from src.services.batch_upload_service import BatchUploadService


def main():
    print("="*60)
    print("VAT Integration Pipeline - Phase 2 Setup")
    print("="*60)

    # Initialize database
    print("\n1. Initializing database...")
    db_manager = get_db_manager()
    db_manager.create_tables()
    print("   ✓ Database initialized")

    # Create VAT periods for 2025
    print("\n2. Creating VAT periods for 2025...")
    period_service = VATPeriodService()

    # Create quarterly periods
    quarterly_periods = period_service.create_quarterly_periods(2025)
    print(f"   ✓ Created {len(quarterly_periods)} quarterly periods")

    for period in quarterly_periods:
        print(f"     - {period['period_name']}: {period['start_date']} to {period['end_date']}")

    # Process sample invoices
    print("\n3. Processing sample invoices...")
    batch_service = BatchUploadService()

    sample_file = project_root / "data" / "input" / "sample_invoices_phase2.csv"

    if sample_file.exists():
        result = batch_service.process_file(
            str(sample_file),
            uploaded_by='setup_script',
            auto_assign_period=True
        )

        print(f"   ✓ Batch upload completed")
        print(f"     - Batch ID: {result['batch_id']}")
        print(f"     - Total: {result['statistics']['total']}")
        print(f"     - Successful: {result['statistics']['successful']}")
        print(f"     - Failed: {result['statistics']['failed']}")
    else:
        print(f"   ⚠ Sample file not found: {sample_file}")

    # Summary
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the API server:")
    print("   python -m uvicorn src.api.main:app --reload")
    print("\n2. Access API documentation:")
    print("   http://localhost:8000/docs")
    print("\n3. Test endpoints:")
    print("   http://localhost:8000/api/invoices")
    print("   http://localhost:8000/api/vat-periods")
    print("="*60)


if __name__ == "__main__":
    main()

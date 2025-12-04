"""Main pipeline runner for VAT integration"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.calculator import VATCalculator
from src.core.validator import DataValidator
from src.core.transformer import DataTransformer
from src.ingestion.reader import DataReader
from src.ingestion.parser import DataParser
from src.utils.logger import setup_logger
from src.utils.exceptions import VATError


class VATPipeline:
    """Main VAT integration pipeline orchestrator"""

    def __init__(self, config_path: str = None):
        """
        Initialize VAT pipeline

        Args:
            config_path: Path to pipeline configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Setup logging
        log_config = self.config.get('logging', {})
        log_file = log_config.get('output', 'logs/pipeline.log')
        log_level = log_config.get('level', 'INFO')
        self.logger = setup_logger('VATPipeline', log_file, log_level)

        # Initialize components
        vat_rates_path = 'config/vat_rates.json'
        self.calculator = VATCalculator(vat_rates_path)
        self.validator = DataValidator(self.config.get('validation', {}))
        self.transformer = DataTransformer()

        self.logger.info("VAT Pipeline initialized")

    def _load_config(self, config_path: str = None) -> Dict:
        """Load pipeline configuration"""
        if not config_path:
            config_path = 'config/pipeline.yaml'

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except FileNotFoundError:
            print(f"Warning: Config file not found: {config_path}, using defaults")
            return self._get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'validation': {
                'strict_mode': True,
                'required_fields': [
                    'transaction_id', 'amount', 'country_code',
                    'transaction_date', 'category'
                ],
                'rules': {}
            },
            'output': {
                'format': 'csv',
                'include_timestamp': True,
                'file_prefix': 'vat_processed'
            },
            'logging': {
                'level': 'INFO'
            },
            'error_handling': {
                'on_validation_error': 'log_and_skip',
                'on_calculation_error': 'log_and_skip',
                'create_error_report': True
            }
        }

    def process(self, input_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Process transactions through the VAT pipeline

        Args:
            input_path: Path to input file
            output_dir: Directory for output files

        Returns:
            dict: Processing results and statistics
        """
        self.logger.info(f"Starting VAT pipeline processing")
        self.logger.info(f"Input: {input_path}")
        self.logger.info(f"Output: {output_dir}")

        results = {
            'processed': 0,
            'valid': 0,
            'invalid': 0,
            'errors': []
        }

        try:
            # 1. Read input data
            self.logger.info("Reading input data...")
            raw_transactions = DataReader.read_file(input_path)
            self.logger.info(f"Read {len(raw_transactions)} transactions")

            # 2. Parse and normalize
            self.logger.info("Parsing transactions...")
            parsed_transactions = DataParser.parse_batch(raw_transactions)

            # 3. Validate transactions
            self.logger.info("Validating transactions...")
            validation_results = self.validator.validate_batch(parsed_transactions)

            # 4. Process valid transactions
            self.logger.info("Calculating VAT...")
            processed_transactions = []
            error_transactions = []

            for transaction in parsed_transactions:
                try:
                    # Validate individual transaction
                    is_valid, error_msg = self.validator.validate_transaction(transaction)

                    if is_valid:
                        # Calculate VAT
                        vat_result = self.calculator.calculate_vat(
                            amount=transaction['amount'],
                            country_code=transaction['country_code'],
                            category=transaction.get('category', 'standard')
                        )

                        # Enrich transaction
                        enriched = self.transformer.enrich_transaction(
                            transaction, vat_result, 'valid'
                        )
                        processed_transactions.append(enriched)
                        results['valid'] += 1
                    else:
                        # Add to errors
                        transaction['validation_status'] = 'invalid'
                        transaction['error'] = error_msg
                        error_transactions.append(transaction)
                        results['invalid'] += 1
                        results['errors'].append({
                            'transaction_id': transaction.get('transaction_id'),
                            'error': error_msg
                        })

                except VATError as e:
                    self.logger.error(
                        f"Error processing transaction "
                        f"{transaction.get('transaction_id')}: {e}"
                    )
                    transaction['validation_status'] = 'error'
                    transaction['error'] = str(e)
                    error_transactions.append(transaction)
                    results['invalid'] += 1
                    results['errors'].append({
                        'transaction_id': transaction.get('transaction_id'),
                        'error': str(e)
                    })

            results['processed'] = len(parsed_transactions)

            # 5. Write output files
            self.logger.info("Writing output files...")
            self._write_output(
                processed_transactions,
                error_transactions,
                output_dir
            )

            # 6. Generate summary
            summary = self.transformer.create_summary_report(processed_transactions)
            results['summary'] = summary

            self.logger.info(
                f"Pipeline complete: {results['valid']} valid, "
                f"{results['invalid']} invalid"
            )

            return results

        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            raise

    def _write_output(
        self,
        processed: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        output_dir: str
    ):
        """Write output files"""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        output_config = self.config.get('output', {})
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_prefix = output_config.get('file_prefix', 'vat_processed')

        # Write processed transactions
        if processed:
            output_file = os.path.join(
                output_dir,
                f"{file_prefix}_{timestamp}.csv"
            )
            self._write_csv(processed, output_file)
            self.logger.info(f"Wrote {len(processed)} processed transactions to {output_file}")

        # Write error report
        if errors and self.config.get('error_handling', {}).get('create_error_report'):
            error_file = os.path.join(
                output_dir,
                f"errors_{timestamp}.csv"
            )
            self._write_csv(errors, error_file)
            self.logger.info(f"Wrote {len(errors)} error records to {error_file}")

        # Write summary report
        if processed:
            summary = self.transformer.create_summary_report(processed)
            summary_file = os.path.join(
                output_dir,
                f"summary_{timestamp}.json"
            )
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Wrote summary report to {summary_file}")

    def _write_csv(self, data: List[Dict[str, Any]], file_path: str):
        """Write data to CSV file"""
        import csv

        if not data:
            return

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


def main():
    """Main entry point for pipeline"""
    parser = argparse.ArgumentParser(
        description='VAT Integration Pipeline - Phase 1'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input file path (CSV or JSON)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory path'
    )
    parser.add_argument(
        '--config',
        default=None,
        help='Configuration file path'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    try:
        # Initialize and run pipeline
        pipeline = VATPipeline(config_path=args.config)
        results = pipeline.process(args.input, args.output)

        # Print summary
        print("\n" + "="*60)
        print("VAT PIPELINE PROCESSING COMPLETE")
        print("="*60)
        print(f"Total transactions: {results['processed']}")
        print(f"Valid: {results['valid']}")
        print(f"Invalid: {results['invalid']}")

        if 'summary' in results:
            summary = results['summary']
            print(f"\nTotal base amount: ${summary['total_base_amount']:,.2f}")
            print(f"Total VAT amount: ${summary['total_vat_amount']:,.2f}")
            print(f"Total amount: ${summary['total_amount']:,.2f}")

        print("="*60)

        # Exit with error code if there were issues
        sys.exit(0 if results['invalid'] == 0 else 1)

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

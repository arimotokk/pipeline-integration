"""Data readers for various input formats"""

import csv
import json
from typing import List, Dict, Any
from pathlib import Path

from ..utils.exceptions import DataIngestionError
from ..utils.logger import get_logger


logger = get_logger(__name__)


class DataReader:
    """Reads transaction data from various file formats"""

    @staticmethod
    def read_csv(file_path: str) -> List[Dict[str, Any]]:
        """
        Read transactions from CSV file

        Args:
            file_path: Path to CSV file

        Returns:
            list: List of transaction dictionaries

        Raises:
            DataIngestionError: If file cannot be read
        """
        try:
            transactions = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    transactions.append(dict(row))

            logger.info(f"Read {len(transactions)} transactions from {file_path}")
            return transactions

        except FileNotFoundError:
            raise DataIngestionError(f"File not found: {file_path}")
        except Exception as e:
            raise DataIngestionError(f"Error reading CSV file: {e}")

    @staticmethod
    def read_json(file_path: str) -> List[Dict[str, Any]]:
        """
        Read transactions from JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            list: List of transaction dictionaries

        Raises:
            DataIngestionError: If file cannot be read
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both array and object formats
            if isinstance(data, list):
                transactions = data
            elif isinstance(data, dict) and 'transactions' in data:
                transactions = data['transactions']
            else:
                raise DataIngestionError("JSON file must contain array or object with 'transactions' key")

            logger.info(f"Read {len(transactions)} transactions from {file_path}")
            return transactions

        except FileNotFoundError:
            raise DataIngestionError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise DataIngestionError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise DataIngestionError(f"Error reading JSON file: {e}")

    @staticmethod
    def read_file(file_path: str) -> List[Dict[str, Any]]:
        """
        Read transactions from file (auto-detect format)

        Args:
            file_path: Path to input file

        Returns:
            list: List of transaction dictionaries

        Raises:
            DataIngestionError: If file format is not supported
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == '.csv':
            return DataReader.read_csv(file_path)
        elif suffix == '.json':
            return DataReader.read_json(file_path)
        else:
            raise DataIngestionError(
                f"Unsupported file format: {suffix}. "
                f"Supported formats: .csv, .json"
            )

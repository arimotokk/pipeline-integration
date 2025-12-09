"""
Database models and operations for VAT Integration Pipeline
Supports both SQLite (local) and PostgreSQL (production)
"""

import os
from datetime import datetime
from contextlib import contextmanager

# Determine which database to use
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (production)
    import psycopg2
    from psycopg2.extras import RealDictCursor
    USE_POSTGRES = True
else:
    # SQLite (local development)
    import sqlite3
    USE_POSTGRES = False
    DB_PATH = 'vat_invoices.db'


@contextmanager
def get_db():
    """Context manager for database connections"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_session(autocommit=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db():
    """Initialize the database with required tables"""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id SERIAL PRIMARY KEY,
                    invoice_number TEXT,
                    date TEXT,
                    supplier_customer TEXT,
                    net_amount REAL NOT NULL,
                    vat_amount REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    invoice_type TEXT NOT NULL,
                    vat_period TEXT NOT NULL,
                    file_path TEXT,
                    file_name TEXT NOT NULL,
                    parsing_error TEXT,
                    manual_entry INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_vat_period 
                ON invoices(vat_period)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_invoice_type 
                ON invoices(invoice_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON invoices(status)
            ''')
        else:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT,
                    date TEXT,
                    supplier_customer TEXT,
                    net_amount REAL NOT NULL,
                    vat_amount REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    invoice_type TEXT NOT NULL,
                    vat_period TEXT NOT NULL,
                    file_path TEXT,
                    file_name TEXT NOT NULL,
                    parsing_error TEXT,
                    manual_entry INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'success',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add status column if it doesn't exist (for existing databases)
            try:
                conn.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'success'")
            except:
                pass  # Column already exists
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_vat_period 
                ON invoices(vat_period)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_invoice_type 
                ON invoices(invoice_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status 
                ON invoices(status)
            ''')


def _execute_query(conn, query, params=None):
    """Execute query with appropriate cursor for database type"""
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return cursor
    else:
        return conn.execute(query, params if params else ())


def _dict_row(row):
    """Convert row to dict"""
    if USE_POSTGRES:
        return dict(row)
    else:
        return dict(row)


def insert_invoice(invoice_data):
    """Insert a new invoice into the database"""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invoices (
                    invoice_number, date, supplier_customer,
                    net_amount, vat_amount, total_amount,
                    invoice_type, vat_period, file_path, file_name, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_name'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                invoice_data.get('file_path'),
                invoice_data['file_name'],
                invoice_data.get('status', 'success')
            ))
            return cursor.fetchone()[0]
        else:
            cursor = conn.execute('''
                INSERT INTO invoices (
                    invoice_number, date, supplier_customer,
                    net_amount, vat_amount, total_amount,
                    invoice_type, vat_period, file_path, file_name, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_name'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                invoice_data.get('file_path'),
                invoice_data['file_name'],
                invoice_data.get('status', 'success')
            ))
            return cursor.lastrowid


def get_all_invoices(order_by='created_at DESC'):
    """Retrieve all invoices from the database"""
    with get_db() as conn:
        cursor = _execute_query(conn, f'''
            SELECT * FROM invoices 
            ORDER BY {order_by}
        ''')
        return [_dict_row(row) for row in cursor.fetchall()]


def get_invoices_by_period(vat_period):
    """Retrieve invoices for a specific VAT period"""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = _execute_query(conn, '''
                SELECT * FROM invoices 
                WHERE vat_period = %s
                ORDER BY created_at DESC
            ''', (vat_period,))
        else:
            cursor = _execute_query(conn, '''
                SELECT * FROM invoices 
                WHERE vat_period = ?
                ORDER BY created_at DESC
            ''', (vat_period,))
        return [_dict_row(row) for row in cursor.fetchall()]


def get_vat_summary_by_period():
    """Calculate VAT summary grouped by period (only success status)"""
    with get_db() as conn:
        cursor = _execute_query(conn, '''
            SELECT 
                vat_period,
                SUM(CASE WHEN invoice_type = 'sales' THEN vat_amount ELSE 0 END) as sales_vat,
                SUM(CASE WHEN invoice_type = 'purchase' THEN vat_amount ELSE 0 END) as purchase_vat,
                SUM(CASE WHEN invoice_type = 'sales' THEN vat_amount ELSE 0 END) - 
                SUM(CASE WHEN invoice_type = 'purchase' THEN vat_amount ELSE 0 END) as net_vat,
                COUNT(*) as invoice_count
            FROM invoices
            WHERE status = 'success'
            GROUP BY vat_period
            ORDER BY vat_period DESC
        ''')
        return [_dict_row(row) for row in cursor.fetchall()]


def get_available_periods():
    """Get list of all VAT periods in the database"""
    with get_db() as conn:
        cursor = _execute_query(conn, '''
            SELECT DISTINCT vat_period 
            FROM invoices 
            ORDER BY vat_period DESC
        ''')
        if USE_POSTGRES:
            return [row['vat_period'] for row in cursor.fetchall()]
        else:
            return [row['vat_period'] for row in cursor.fetchall()]


def generate_vat_periods():
    """Generate list of VAT periods (quarters) for the last 2 years"""
    current_year = datetime.now().year
    periods = []
    
    for year in range(current_year - 1, current_year + 2):
        for quarter in range(1, 5):
            periods.append(f"Q{quarter} {year}")
    
    return periods


def insert_failed_invoice(file_name, error_message):
    """Insert a failed invoice record for manual review"""
    with get_db() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invoices (
                    invoice_number, date, supplier_customer,
                    net_amount, vat_amount, total_amount,
                    invoice_type, vat_period, file_name, parsing_error
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                'PENDING', '', '', 0.0, 0.0, 0.0,
                'unknown', 'PENDING', file_name, error_message
            ))
            return cursor.fetchone()[0]
        else:
            cursor = conn.execute('''
                INSERT INTO invoices (
                    invoice_number, date, supplier_customer,
                    net_amount, vat_amount, total_amount,
                    invoice_type, vat_period, file_name, parsing_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                'PENDING', '', '', 0.0, 0.0, 0.0,
                'unknown', 'PENDING', file_name, error_message
            ))
            return cursor.lastrowid


def get_failed_invoices():
    """Get all invoices that failed to parse"""
    with get_db() as conn:
        cursor = _execute_query(conn, '''
            SELECT * FROM invoices 
            WHERE parsing_error IS NOT NULL AND parsing_error != ''
            ORDER BY created_at DESC
        ''')
        return [_dict_row(row) for row in cursor.fetchall()]


def update_invoice_from_manual_entry(invoice_id, invoice_data):
    """Update a failed invoice with manually entered data"""
    with get_db() as conn:
        if USE_POSTGRES:
            conn.cursor().execute('''
                UPDATE invoices
                SET invoice_number = %s,
                    date = %s,
                    supplier_customer = %s,
                    net_amount = %s,
                    vat_amount = %s,
                    total_amount = %s,
                    invoice_type = %s,
                    vat_period = %s,
                    parsing_error = NULL,
                    manual_entry = 1
                WHERE id = %s
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_customer'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                invoice_id
            ))
        else:
            conn.execute('''
                UPDATE invoices
                SET invoice_number = ?,
                    date = ?,
                    supplier_customer = ?,
                    net_amount = ?,
                    vat_amount = ?,
                    total_amount = ?,
                    invoice_type = ?,
                    vat_period = ?,
                    parsing_error = NULL,
                    manual_entry = 1
                WHERE id = ?
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_customer'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                invoice_id
            ))


def delete_invoice(invoice_id):
    """Delete an invoice from the database"""
    with get_db() as conn:
        if USE_POSTGRES:
            conn.cursor().execute('DELETE FROM invoices WHERE id = %s', (invoice_id,))
        else:
            conn.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))


def update_invoice(invoice_id, invoice_data):
    """Update an existing invoice with new data"""
    with get_db() as conn:
        if USE_POSTGRES:
            conn.cursor().execute('''
                UPDATE invoices
                SET invoice_number = %s,
                    date = %s,
                    supplier_customer = %s,
                    net_amount = %s,
                    vat_amount = %s,
                    total_amount = %s,
                    invoice_type = %s,
                    vat_period = %s,
                    status = %s,
                    parsing_error = NULL
                WHERE id = %s
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_customer'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                'success',
                invoice_id
            ))
        else:
            conn.execute('''
                UPDATE invoices
                SET invoice_number = ?,
                    date = ?,
                    supplier_customer = ?,
                    net_amount = ?,
                    vat_amount = ?,
                    total_amount = ?,
                    invoice_type = ?,
                    vat_period = ?,
                    status = ?,
                    parsing_error = NULL
                WHERE id = ?
            ''', (
                invoice_data.get('invoice_number'),
                invoice_data.get('date'),
                invoice_data.get('supplier_customer'),
                invoice_data['net_amount'],
                invoice_data['vat_amount'],
                invoice_data['total_amount'],
                invoice_data['invoice_type'],
                invoice_data['vat_period'],
                'success',
                invoice_id
            ))


def get_error_invoices():
    """Get all invoices with error or pending_review status"""
    with get_db() as conn:
        cursor = _execute_query(conn, '''
            SELECT * FROM invoices 
            WHERE status IN ('error', 'pending_review')
            ORDER BY created_at DESC
        ''')
        return [_dict_row(row) for row in cursor.fetchall()]


def get_error_count():
    """Get count of invoices with error status"""
    with get_db() as conn:
        cursor = _execute_query(conn, '''
            SELECT COUNT(*) as count FROM invoices 
            WHERE status IN ('error', 'pending_review')
        ''')
        result = cursor.fetchone()
        if USE_POSTGRES:
            return result['count']
        else:
            return result['count']

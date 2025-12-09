"""
VAT Integration Pipeline - Deployment Version
Flask app with PostgreSQL and Cloudflare R2 for cloud deployment
"""

import os
import io
import boto3
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_httpauth import HTTPBasicAuth
from anthropic import Anthropic
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import json
from datetime import datetime
import database
import reports

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize HTTP Basic Authentication
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    """Verify username and password from environment variables"""
    auth_username = os.getenv('AUTH_USERNAME')
    auth_password = os.getenv('AUTH_PASSWORD')
    
    print(f"[AUTH DEBUG] Received username: '{username}'")
    print(f"[AUTH DEBUG] Received password: '{password}'")
    print(f"[AUTH DEBUG] Expected username: '{auth_username}'")
    print(f"[AUTH DEBUG] Expected password: '{auth_password}'")
    
    if auth_username and auth_password:
        if username == auth_username and password == auth_password:
            print("[AUTH DEBUG] ✓ Authentication successful!")
            return username
    print("[AUTH DEBUG] ✗ Authentication failed!")
    return None

# Initialize Anthropic client
client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# VAT rates
VAT_RATE = 0.20  # 20% standard UK VAT rate

# Initialize S3 client for Cloudflare R2
USE_R2 = os.getenv('R2_ENDPOINT_URL') is not None

if USE_R2:
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('R2_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name='auto'
    )
    R2_BUCKET = os.getenv('R2_BUCKET_NAME')
else:
    # Local file storage
    app.config['UPLOAD_FOLDER'] = 'uploads'
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
database.init_db()


def save_file(file_content, filename):
    """Save file to R2 or local storage"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    
    if USE_R2:
        # Upload to R2
        s3_client.put_object(
            Bucket=R2_BUCKET,
            Key=f"invoices/{unique_filename}",
            Body=file_content.encode('utf-8') if isinstance(file_content, str) else file_content
        )
        return f"r2://invoices/{unique_filename}"
    else:
        # Save locally
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        with open(file_path, 'w') as f:
            f.write(file_content)
        return file_path


def get_file(file_path):
    """Retrieve file from R2 or local storage"""
    if file_path.startswith('r2://'):
        # Download from R2
        key = file_path.replace('r2://', '')
        response = s3_client.get_object(Bucket=R2_BUCKET, Key=key)
        return response['Body'].read().decode('utf-8')
    else:
        # Read from local storage
        with open(file_path, 'r') as f:
            return f.read()


def extract_invoice_data(file_content, file_name):
    """
    Use Claude to extract structured data from invoice
    """
    prompt = f"""You are analyzing an invoice file named "{file_name}".

Please extract the following information from this invoice:
- Invoice Number
- Date
- Supplier/Customer Name
- Net Amount (amount before VAT)
- VAT Amount (if present)
- Total Amount

Return the data in JSON format with these exact keys:
{{
    "invoice_number": "...",
    "date": "...",
    "supplier_name": "...",
    "net_amount": 0.00,
    "vat_amount": 0.00,
    "total_amount": 0.00
}}

If any field is not found, use empty string for text fields or 0.00 for numeric fields.
Only return the JSON, no other text.

Invoice content:
{file_content}
"""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract JSON from response
        response_text = message.content[0].text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        invoice_data = json.loads(response_text)
        return invoice_data
    
    except Exception as e:
        raise Exception(f"Error extracting invoice data: {str(e)}")


def calculate_vat(invoice_data, transaction_type):
    """
    Calculate VAT amounts based on transaction type
    """
    net_amount = float(invoice_data.get('net_amount', 0))
    vat_amount = float(invoice_data.get('vat_amount', 0))
    total_amount = float(invoice_data.get('total_amount', 0))
    
    # If VAT amount is missing, calculate it
    if vat_amount == 0 and net_amount > 0:
        vat_amount = net_amount * VAT_RATE
    
    # If total is missing, calculate it
    if total_amount == 0 and net_amount > 0:
        total_amount = net_amount + vat_amount
    
    # Determine VAT impact based on transaction type
    if transaction_type == 'sales':
        vat_position = 'Output VAT (owed to HMRC)'
        vat_impact = f'+£{vat_amount:.2f}'
    else:  # purchase
        vat_position = 'Input VAT (reclaimable from HMRC)'
        vat_impact = f'-£{vat_amount:.2f}'
    
    return {
        'net_amount': net_amount,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'vat_rate': VAT_RATE * 100,  # Convert to percentage
        'vat_position': vat_position,
        'vat_impact': vat_impact
    }


@app.route('/')
@auth.login_required
def index():
    """Home page with upload form"""
    vat_periods = database.generate_vat_periods()
    return render_template('upload.html', vat_periods=vat_periods)


@app.route('/upload', methods=['POST'])
@auth.login_required
def upload():
    """Handle batch file upload and process invoices"""
    try:
        # Get form data
        transaction_type = request.form.get('transaction_type', 'sales')
        vat_period = request.form.get('vat_period')
        
        if not vat_period:
            vat_periods = database.generate_vat_periods()
            return render_template('upload.html', vat_periods=vat_periods, 
                                 error='Please select a VAT period')
        
        # Check if files were uploaded
        if 'invoice_files' not in request.files:
            vat_periods = database.generate_vat_periods()
            return render_template('upload.html', vat_periods=vat_periods,
                                 error='No files uploaded')
        
        files = request.files.getlist('invoice_files')
        
        if not files or all(f.filename == '' for f in files):
            vat_periods = database.generate_vat_periods()
            return render_template('upload.html', vat_periods=vat_periods,
                                 error='No files selected')
        
        # Process each file
        processed_invoices = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # Save file
                filename = secure_filename(file.filename)
                
                # Read file content
                file_content = file.read().decode('utf-8', errors='ignore')
                
                # Save the file to R2 or local storage
                file_path = save_file(file_content, filename)
                
                # Extract invoice data using Claude
                invoice_data = extract_invoice_data(file_content, filename)
                
                # Calculate VAT
                vat_calculation = calculate_vat(invoice_data, transaction_type)
                
                # Determine status based on data quality
                status = 'success'
                parsing_error = None
                error_reasons = []
                
                # Check for errors
                if vat_calculation['net_amount'] == 0:
                    error_reasons.append('Net amount is £0.00')
                if vat_calculation['vat_amount'] == 0:
                    error_reasons.append('VAT amount is £0.00')
                if vat_calculation['total_amount'] == 0:
                    error_reasons.append('Total is £0.00')
                
                if (not invoice_data.get('invoice_number') or 
                    invoice_data.get('invoice_number', '').strip() in ['', 'N/A', 'PENDING']):
                    error_reasons.append('Invoice number is N/A or missing')
                
                if (not invoice_data.get('date') or 
                    invoice_data.get('date', '').strip() in ['', 'N/A']):
                    error_reasons.append('Date is N/A or missing')
                
                if (not invoice_data.get('supplier_name') or 
                    invoice_data.get('supplier_name', '').strip() in ['', 'N/A']):
                    error_reasons.append('Supplier/Customer is N/A or missing')
                
                if vat_calculation['net_amount'] > 100000:
                    error_reasons.append(f'Net amount (£{vat_calculation["net_amount"]:.2f}) exceeds £100,000 (likely extraction error)')
                
                if vat_calculation['vat_amount'] > 50000:
                    error_reasons.append(f'VAT amount (£{vat_calculation["vat_amount"]:.2f}) exceeds £50,000 (likely extraction error)')
                
                # Set status and error message if any errors found
                if error_reasons:
                    status = 'error'
                    parsing_error = '; '.join(error_reasons)
                
                # Prepare data for database
                db_data = {
                    'invoice_number': invoice_data.get('invoice_number'),
                    'date': invoice_data.get('date'),
                    'supplier_name': invoice_data.get('supplier_name'),
                    'net_amount': vat_calculation['net_amount'],
                    'vat_amount': vat_calculation['vat_amount'],
                    'total_amount': vat_calculation['total_amount'],
                    'invoice_type': transaction_type,
                    'vat_period': vat_period,
                    'file_path': file_path,
                    'file_name': filename,
                    'status': status
                }
                
                # Insert into database
                invoice_id = database.insert_invoice(db_data)
                
                # Update with parsing error if needed
                if parsing_error:
                    with database.get_db() as conn:
                        if database.USE_POSTGRES:
                            conn.cursor().execute('UPDATE invoices SET parsing_error = %s WHERE id = %s', 
                                           (parsing_error, invoice_id))
                        else:
                            conn.execute('UPDATE invoices SET parsing_error = ? WHERE id = ?', 
                                       (parsing_error, invoice_id))
                
                # Add to processed list
                processed_invoices.append({
                    'id': invoice_id,
                    'file_name': filename,
                    'invoice_number': invoice_data.get('invoice_number'),
                    'net_amount': vat_calculation['net_amount'],
                    'vat_amount': vat_calculation['vat_amount'],
                    'total_amount': vat_calculation['total_amount']
                })
                
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
                # Insert failed invoice for manual entry
                try:
                    database.insert_failed_invoice(file.filename, str(e))
                except Exception as db_error:
                    print(f"Error logging failed invoice: {db_error}")
        
        # Render results
        return render_template('results.html', 
                             invoices=processed_invoices,
                             transaction_type=transaction_type.capitalize(),
                             vat_period=vat_period,
                             errors=errors,
                             batch_mode=True)
    
    except Exception as e:
        vat_periods = database.generate_vat_periods()
        return render_template('upload.html', vat_periods=vat_periods,
                             error=f'Error processing invoices: {str(e)}')


@app.route('/history')
@auth.login_required
def history():
    """Show all uploaded invoices"""
    invoices = database.get_all_invoices()
    return render_template('history.html', invoices=invoices)


@app.route('/vat-summary')
@auth.login_required
def vat_summary():
    """Show VAT summary by period"""
    summary = database.get_vat_summary_by_period()
    error_count = database.get_error_count()
    return render_template('vat_summary.html', summary=summary, error_count=error_count)


@app.route('/download-excel')
@auth.login_required
def download_excel():
    """Download Excel report"""
    try:
        excel_file = reports.generate_excel_report()
        filename = f"VAT_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return f"Error generating Excel report: {str(e)}", 500


@app.route('/download-pdf')
@auth.login_required
def download_pdf():
    """Download PDF report"""
    try:
        pdf_file = reports.generate_pdf_report()
        filename = f"VAT_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            pdf_file,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return f"Error generating PDF report: {str(e)}", 500


@app.route('/errors')
@auth.login_required
def errors():
    """Show failed invoices that need manual entry"""
    failed_invoices = database.get_failed_invoices()
    return render_template('error_dashboard.html', failed_invoices=failed_invoices)


@app.route('/error-review')
@auth.login_required
def error_review():
    """Show error review dashboard"""
    error_invoices = database.get_error_invoices()
    return render_template('error_review.html', error_invoices=error_invoices)


@app.route('/manual-entry/<int:invoice_id>')
@auth.login_required
def manual_entry(invoice_id):
    """Show manual entry form for a failed invoice"""
    with database.get_db() as conn:
        cursor = database._execute_query(conn, 'SELECT * FROM invoices WHERE id = %s' if database.USE_POSTGRES else 'SELECT * FROM invoices WHERE id = ?', 
                                        (invoice_id,))
        invoice = dict(cursor.fetchone())
    
    vat_periods = database.generate_vat_periods()
    return render_template('manual_entry_simple.html', invoice=invoice, vat_periods=vat_periods)


@app.route('/manual-entry/submit', methods=['POST'])
@auth.login_required
def submit_manual_entry():
    """Process manual invoice entry"""
    try:
        invoice_id = int(request.form.get('invoice_id'))
        
        # Calculate total if not provided
        net_amount = float(request.form.get('net_amount', 0))
        vat_amount = float(request.form.get('vat_amount', 0))
        total_amount = float(request.form.get('total_amount', 0))
        
        if total_amount == 0:
            total_amount = net_amount + vat_amount
        
        invoice_data = {
            'invoice_number': request.form.get('invoice_number'),
            'date': request.form.get('date'),
            'supplier_customer': request.form.get('supplier_customer'),
            'net_amount': net_amount,
            'vat_amount': vat_amount,
            'total_amount': total_amount,
            'invoice_type': request.form.get('invoice_type'),
            'vat_period': request.form.get('vat_period')
        }
        
        # Update the invoice
        database.update_invoice_from_manual_entry(invoice_id, invoice_data)
        
        return redirect(url_for('errors'))
    
    except Exception as e:
        return f"Error saving manual entry: {str(e)}", 500


@app.route('/delete/<int:invoice_id>', methods=['POST'])
@auth.login_required
def delete_invoice(invoice_id):
    """Delete an invoice"""
    try:
        # Get invoice file path before deleting
        with database.get_db() as conn:
            cursor = database._execute_query(conn, 'SELECT file_path FROM invoices WHERE id = %s' if database.USE_POSTGRES else 'SELECT file_path FROM invoices WHERE id = ?', 
                                            (invoice_id,))
            row = cursor.fetchone()
            if row:
                file_path = row['file_path'] if database.USE_POSTGRES else row['file_path']
                # Delete file if it exists
                if file_path:
                    if file_path.startswith('r2://'):
                        # Delete from R2
                        key = file_path.replace('r2://', '')
                        s3_client.delete_object(Bucket=R2_BUCKET, Key=key)
                    elif os.path.exists(file_path):
                        # Delete local file
                        os.remove(file_path)
        
        # Delete from database
        database.delete_invoice(invoice_id)
        
        return redirect(url_for('history'))
    
    except Exception as e:
        return f"Error deleting invoice: {str(e)}", 500


@app.route('/flag-error/<int:invoice_id>', methods=['POST'])
@auth.login_required
def flag_error(invoice_id):
    """Manually flag an invoice as error"""
    try:
        with database.get_db() as conn:
            # Update status to error and add a note
            if database.USE_POSTGRES:
                conn.cursor().execute('''
                    UPDATE invoices 
                    SET status = 'error',
                        parsing_error = COALESCE(parsing_error || '; ', '') || 'Manually flagged by user'
                    WHERE id = %s
                ''', (invoice_id,))
            else:
                conn.execute('''
                    UPDATE invoices 
                    SET status = 'error',
                        parsing_error = COALESCE(parsing_error || '; ', '') || 'Manually flagged by user'
                    WHERE id = ?
                ''', (invoice_id,))
        
        return redirect(url_for('history'))
    
    except Exception as e:
        return f"Error flagging invoice: {str(e)}", 500


@app.route('/edit/<int:invoice_id>')
@auth.login_required
def edit_invoice(invoice_id):
    """Show edit form for an invoice"""
    try:
        with database.get_db() as conn:
            cursor = database._execute_query(conn, 'SELECT * FROM invoices WHERE id = %s' if database.USE_POSTGRES else 'SELECT * FROM invoices WHERE id = ?', 
                                            (invoice_id,))
            invoice = cursor.fetchone()
            
            if not invoice:
                return "Invoice not found", 404
            
            invoice = dict(invoice)
        
        vat_periods = database.generate_vat_periods()
        return render_template('edit_invoice.html', invoice=invoice, vat_periods=vat_periods)
    
    except Exception as e:
        return f"Error loading invoice: {str(e)}", 500


@app.route('/edit/submit', methods=['POST'])
@auth.login_required
def submit_edit():
    """Process invoice edit"""
    try:
        invoice_id = int(request.form.get('invoice_id'))
        
        # Calculate total if not provided
        net_amount = float(request.form.get('net_amount', 0))
        vat_amount = float(request.form.get('vat_amount', 0))
        total_amount = float(request.form.get('total_amount', 0))
        
        if total_amount == 0:
            total_amount = net_amount + vat_amount
        
        invoice_data = {
            'invoice_number': request.form.get('invoice_number'),
            'date': request.form.get('date'),
            'supplier_customer': request.form.get('supplier_customer'),
            'net_amount': net_amount,
            'vat_amount': vat_amount,
            'total_amount': total_amount,
            'invoice_type': request.form.get('invoice_type'),
            'vat_period': request.form.get('vat_period')
        }
        
        # Update the invoice
        database.update_invoice(invoice_id, invoice_data)
        
        return redirect(url_for('history'))
    
    except Exception as e:
        return f"Error saving changes: {str(e)}", 500


@app.route('/health')
def health():
    """Health check endpoint for monitoring (no authentication required)"""
    return {'status': 'healthy'}, 200


if __name__ == '__main__':
    # Check if API key is set
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("Warning: ANTHROPIC_API_KEY not set in .env file")
    
    print("Starting VAT Integration Pipeline - Deployment Version")
    print("Features: PostgreSQL | Cloudflare R2 | Batch Upload | Reports | Error Handling")
    port = int(os.getenv('PORT', 5002))
    app.run(debug=False, host='0.0.0.0', port=port)

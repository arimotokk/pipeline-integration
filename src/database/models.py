"""Database models for VAT pipeline Phase 2"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Invoice(Base):
    """Invoice model for storing processed invoices"""
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)

    # Invoice details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='EUR', nullable=False)
    country_code = Column(String(2), nullable=False, index=True)
    invoice_date = Column(String(10), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)

    # Customer/vendor info
    customer_name = Column(String(200))
    customer_vat_number = Column(String(50))
    vendor_name = Column(String(200))
    vendor_vat_number = Column(String(50))

    # VAT calculations
    vat_rate = Column(Float, nullable=False)
    vat_amount = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)

    # VAT period
    vat_period_id = Column(Integer, ForeignKey('vat_periods.id'), index=True)
    vat_period = relationship("VATPeriod", back_populates="invoices")

    # Validation and processing
    validation_status = Column(String(20), nullable=False, index=True)
    processing_status = Column(String(20), default='completed', index=True)
    error_message = Column(Text, nullable=True)

    # Batch upload tracking
    batch_upload_id = Column(Integer, ForeignKey('batch_uploads.id'), index=True)
    batch_upload = relationship("BatchUpload", back_populates="invoices")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_by = Column(String(50), default='system')

    # Additional fields
    description = Column(Text)
    notes = Column(Text)
    is_deleted = Column(Boolean, default=False, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_date_country', 'invoice_date', 'country_code'),
        Index('idx_status', 'validation_status', 'processing_status'),
        Index('idx_period_status', 'vat_period_id', 'validation_status'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'transaction_id': self.transaction_id,
            'amount': self.amount,
            'currency': self.currency,
            'country_code': self.country_code,
            'invoice_date': self.invoice_date,
            'category': self.category,
            'customer_name': self.customer_name,
            'customer_vat_number': self.customer_vat_number,
            'vendor_name': self.vendor_name,
            'vendor_vat_number': self.vendor_vat_number,
            'vat_rate': self.vat_rate,
            'vat_amount': self.vat_amount,
            'total_amount': self.total_amount,
            'vat_period_id': self.vat_period_id,
            'validation_status': self.validation_status,
            'processing_status': self.processing_status,
            'error_message': self.error_message,
            'batch_upload_id': self.batch_upload_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processed_by': self.processed_by,
            'description': self.description,
            'notes': self.notes
        }


class VATPeriod(Base):
    """VAT Period model for managing reporting periods"""
    __tablename__ = 'vat_periods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_name = Column(String(50), unique=True, nullable=False, index=True)

    # Period dates
    start_date = Column(String(10), nullable=False, index=True)
    end_date = Column(String(10), nullable=False, index=True)

    # Period type
    period_type = Column(String(20), nullable=False)  # monthly, quarterly, annual
    year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=True, index=True)  # 1-4 for quarterly
    month = Column(Integer, nullable=True, index=True)   # 1-12 for monthly

    # Status
    status = Column(String(20), default='open', nullable=False, index=True)  # open, closed, submitted

    # Summary statistics
    total_invoices = Column(Integer, default=0)
    total_base_amount = Column(Float, default=0.0)
    total_vat_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)

    # Relationships
    invoices = relationship("Invoice", back_populates="vat_period")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(String(50), nullable=True)

    __table_args__ = (
        Index('idx_year_quarter', 'year', 'quarter'),
        Index('idx_year_month', 'year', 'month'),
        Index('idx_date_range', 'start_date', 'end_date'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'period_name': self.period_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'period_type': self.period_type,
            'year': self.year,
            'quarter': self.quarter,
            'month': self.month,
            'status': self.status,
            'total_invoices': self.total_invoices,
            'total_base_amount': self.total_base_amount,
            'total_vat_amount': self.total_vat_amount,
            'total_amount': self.total_amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'submitted_by': self.submitted_by
        }


class BatchUpload(Base):
    """Batch upload tracking model"""
    __tablename__ = 'batch_uploads'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(100), unique=True, nullable=False, index=True)

    # Upload details
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # csv, json, xlsx
    file_size = Column(Integer)  # bytes

    # Processing status
    status = Column(String(20), default='pending', nullable=False, index=True)
    # pending, processing, completed, failed

    # Statistics
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)

    # Relationships
    invoices = relationship("Invoice", back_populates="batch_upload")

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Metadata
    uploaded_by = Column(String(50), default='system')
    output_path = Column(String(500))

    __table_args__ = (
        Index('idx_status_date', 'status', 'created_at'),
    )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'status': self.status,
            'total_records': self.total_records,
            'processed_records': self.processed_records,
            'failed_records': self.failed_records,
            'successful_records': self.successful_records,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploaded_by': self.uploaded_by,
            'output_path': self.output_path
        }

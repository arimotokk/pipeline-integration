"""Database connection and session management"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import os

from .models import Base
from ..utils.logger import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: str = None):
        """
        Initialize database manager

        Args:
            database_url: Database URL (defaults to SQLite)
        """
        if database_url is None:
            # Default to SQLite in data directory
            db_path = os.path.join('data', 'vat_pipeline.db')
            os.makedirs('data', exist_ok=True)
            database_url = f'sqlite:///{db_path}'

        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None

        self._initialize()

    def _initialize(self):
        """Initialize database engine and session factory"""
        try:
            # Create engine
            if 'sqlite' in self.database_url:
                # SQLite specific settings
                self.engine = create_engine(
                    self.database_url,
                    connect_args={'check_same_thread': False},
                    poolclass=StaticPool
                )
            else:
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20
                )

            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"Database initialized: {self.database_url}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope for database operations"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction error: {e}")
            raise
        finally:
            session.close()

    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
_db_manager = None


def get_db_manager(database_url: str = None) -> DatabaseManager:
    """Get or create global database manager"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
        _db_manager.create_tables()
    return _db_manager


def get_db_session():
    """Get a database session (for dependency injection)"""
    db_manager = get_db_manager()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

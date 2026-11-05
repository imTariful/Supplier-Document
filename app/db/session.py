"""
SQLAlchemy Session and Database Engine Configuration for SQLite.
"""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default SQLite database path
DEFAULT_DB_DIR = Path("./data").resolve()
DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)

# Uploads directory
UPLOADS_DIR = Path("./data/uploads").resolve()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DEFAULT_DB_DIR / "supplier_verification.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# SQLite connect args to allow multithreading safely
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency helper to yield a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

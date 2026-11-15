"""
Database module for PhysioSignal OS.
SQLite + SQLAlchemy for persistent storage of patients and analyses.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

# Database setup
DB_PATH = Path("data/physiosignal.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Patient(Base):
    """Patient model with abstracted ID for HIPAA compliance."""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_hash = Column(String(64), unique=True, index=True)  # SHA-256 hash of real ID
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

class Analysis(Base):
    """Analysis result model."""
    __tablename__ = "analyses"
    
    id = Column(String(16), primary_key=True)  # analysis_id from API
    patient_hash = Column(String(64), index=True)
    signal_type = Column(String(16))  # emg, eeg, ecg, psg, ppg
    exam_type = Column(String(32))
    algorithm_id = Column(String(32))
    parameters = Column(JSON)
    metrics = Column(JSON)
    input_hash = Column(String(64))
    output_hash = Column(String(64))
    report_path = Column(String(256))
    status = Column(String(16))  # success, failed, pending
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print("✅ Database module created")

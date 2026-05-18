from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Index
from backend.app.db.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True)  # LEI as primary key
    lei = Column(String(20), unique=True, nullable=False, index=True)
    legal_name = Column(String(512), nullable=False)
    normalized_name = Column(String(512), nullable=True, index=True)
    other_names = Column(Text, nullable=True)         # JSON array stored as text
    country = Column(String(3), nullable=True, index=True)
    jurisdiction = Column(String(128), nullable=True, index=True)
    entity_status = Column(String(64), nullable=True, index=True)
    registration_status = Column(String(64), nullable=True)
    legal_address = Column(Text, nullable=True)
    headquarters_address = Column(Text, nullable=True)
    managing_lou = Column(String(128), nullable=True)
    initial_registration_date = Column(DateTime, nullable=True)
    last_update_date = Column(DateTime, nullable=True)
    source = Column(String(64), nullable=True, default="GLEIF")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_entities_normalized_name", "normalized_name"),
        Index("ix_entities_country_status", "country", "entity_status"),
    )


class EntityAlias(Base):
    __tablename__ = "entity_aliases"

    id = Column(String, primary_key=True)
    lei = Column(String(20), nullable=False, index=True)
    alias_name = Column(String(512), nullable=False)
    alias_type = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"

    id = Column(String, primary_key=True)
    run_date = Column(DateTime, default=datetime.utcnow)
    total_records = Column(String, nullable=True)
    valid_records = Column(String, nullable=True)
    invalid_records = Column(String, nullable=True)
    missing_name_rate = Column(String, nullable=True)
    missing_address_rate = Column(String, nullable=True)
    duplicate_lei_count = Column(String, nullable=True)
    pipeline_runtime_seconds = Column(String, nullable=True)
    data_quality_score = Column(String, nullable=True)
    report_path = Column(String, nullable=True)


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(String, primary_key=True)
    lei = Column(String(20), nullable=False, index=True)
    report_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

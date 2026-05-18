from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text, Index
from backend.app.db.database import Base


class EntityResolutionMatch(Base):
    __tablename__ = "entity_resolution_matches"

    id = Column(String, primary_key=True)
    lei_a = Column(String(20), nullable=False, index=True)
    lei_b = Column(String(20), nullable=False, index=True)
    name_a = Column(String(512), nullable=True)
    name_b = Column(String(512), nullable=True)
    name_similarity = Column(Float, nullable=True)
    address_similarity = Column(Float, nullable=True)
    embedding_similarity = Column(Float, nullable=True)
    country_match = Column(Float, nullable=True)
    jurisdiction_match = Column(Float, nullable=True)
    final_score = Column(Float, nullable=False, index=True)
    decision = Column(String(32), nullable=False, index=True)  # same_entity | needs_review | different_entity
    reason_codes = Column(Text, nullable=True)   # JSON array
    reviewer_decision = Column(String(32), nullable=True)  # accepted | rejected
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_erm_decision_score", "decision", "final_score"),
    )

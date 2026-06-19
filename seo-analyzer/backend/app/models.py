"""
Database models for storing audit results and history.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AuditResult(Base):
    """Stores complete audit results for a URL."""

    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Overall score
    health_score = Column(Float, nullable=True)

    # Category scores (0-100 each)
    technical_score = Column(Float, nullable=True)
    content_score = Column(Float, nullable=True)
    onpage_score = Column(Float, nullable=True)
    schema_score = Column(Float, nullable=True)
    performance_score = Column(Float, nullable=True)
    security_score = Column(Float, nullable=True)

    # Detected site type
    site_type = Column(String(50), nullable=True)  # saas, ecommerce, local, publisher, agency

    # Full results as JSON
    results = Column(JSON, nullable=True)

    # Issues summary
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)


class DriftBaseline(Base):
    """Stores SEO baselines for drift comparison over time."""

    __tablename__ = "drift_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2048), nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.utcnow)

    # Snapshot data
    title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1_tags = Column(JSON, nullable=True)
    word_count = Column(Integer, nullable=True)
    internal_links_count = Column(Integer, nullable=True)
    external_links_count = Column(Integer, nullable=True)
    schema_types = Column(JSON, nullable=True)
    canonical_url = Column(String(2048), nullable=True)
    robots_directives = Column(JSON, nullable=True)
    health_score = Column(Float, nullable=True)

    # Full baseline data
    baseline_data = Column(JSON, nullable=True)

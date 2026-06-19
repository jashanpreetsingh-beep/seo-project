"""
Pydantic schemas for API request/response validation.
"""
from __future__ import annotations


from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, HttpUrl, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SiteType(str, Enum):
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    LOCAL = "local"
    PUBLISHER = "publisher"
    AGENCY = "agency"
    OTHER = "other"


class AuditStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Request Schemas ──────────────────────────────────────────────────────────

class AuditRequest(BaseModel):
    """Request to start a new SEO audit."""
    url: str = Field(..., description="URL to analyze", examples=["https://example.com"])


# ─── Issue Schema ─────────────────────────────────────────────────────────────

class SEOIssue(BaseModel):
    """A single SEO issue found during analysis."""
    severity: Severity
    category: str  # technical, content, onpage, schema, performance, security
    title: str
    description: str
    recommendation: str
    impact: str = ""  # How this affects rankings


# ─── Category Result Schemas ──────────────────────────────────────────────────

class TechnicalResult(BaseModel):
    score: float = 0
    robots_txt: dict = {}
    sitemap: dict = {}
    canonicals: dict = {}
    redirects: dict = {}
    https: dict = {}
    mobile_friendly: dict = {}
    issues: list[SEOIssue] = []


class ContentResult(BaseModel):
    score: float = 0
    word_count: int = 0
    readability: dict = {}
    headings: dict = {}
    eeat_signals: dict = {}
    thin_content: bool = False
    issues: list[SEOIssue] = []


class OnPageResult(BaseModel):
    score: float = 0
    title: dict = {}
    meta_description: dict = {}
    headings: dict = {}
    images: dict = {}
    internal_links: dict = {}
    external_links: dict = {}
    issues: list[SEOIssue] = []


class SchemaResult(BaseModel):
    score: float = 0
    schemas_found: list[dict] = []
    validation_errors: list[str] = []
    suggestions: list[str] = []
    issues: list[SEOIssue] = []


class PerformanceResult(BaseModel):
    score: float = 0
    lcp: dict = {}  # Largest Contentful Paint
    inp: dict = {}  # Interaction to Next Paint
    cls: dict = {}  # Cumulative Layout Shift
    fcp: dict = {}  # First Contentful Paint
    ttfb: dict = {}  # Time to First Byte
    page_size: dict = {}
    issues: list[SEOIssue] = []


class SecurityResult(BaseModel):
    score: float = 0
    https: dict = {}
    headers: dict = {}
    mixed_content: list[str] = []
    issues: list[SEOIssue] = []


# ─── Full Audit Response ──────────────────────────────────────────────────────

class AuditResponse(BaseModel):
    """Complete audit result returned to the frontend."""
    id: Optional[int] = None
    url: str
    status: AuditStatus = AuditStatus.COMPLETED
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Overall
    health_score: float = 0
    site_type: SiteType = SiteType.OTHER

    # Category results
    technical: TechnicalResult = TechnicalResult()
    content: ContentResult = ContentResult()
    onpage: OnPageResult = OnPageResult()
    schema_markup: SchemaResult = SchemaResult()
    performance: PerformanceResult = PerformanceResult()
    security: SecurityResult = SecurityResult()

    # Aggregated issues
    issues: list[SEOIssue] = []
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Recommendations (prioritized)
    recommendations: list[dict] = []


class AuditHistoryItem(BaseModel):
    """Summary item for audit history list."""
    id: int
    url: str
    health_score: float
    site_type: Optional[str] = None
    created_at: datetime
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

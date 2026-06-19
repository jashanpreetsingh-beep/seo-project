"""
Audit API Routes.

POST /api/audit       — Start a new SEO audit
GET  /api/audit/:id   — Get audit results by ID
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.graph.workflow import run_audit
from app.models import AuditResult
from app.schemas import AuditRequest, AuditResponse, AuditStatus

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.post("", response_model=AuditResponse)
async def create_audit(request: AuditRequest, db: AsyncSession = Depends(get_db)):
    """
    Run a full SEO audit on the provided URL.
    
    This triggers the LangGraph workflow which:
    1. Fetches the page
    2. Runs 6 analyzers (technical, content, onpage, schema, performance, security)
    3. Scores and prioritizes findings
    4. Returns the complete report
    
    Takes 10-30 seconds depending on the target site.
    """
    url = request.url.strip()

    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        # Run the LangGraph audit workflow
        results = await run_audit(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

    # Calculate issue counts
    issues = results.get("issues", [])
    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    high_count = sum(1 for i in issues if i.get("severity") == "high")
    medium_count = sum(1 for i in issues if i.get("severity") == "medium")
    low_count = sum(1 for i in issues if i.get("severity") == "low")

    # Save to database
    audit_record = AuditResult(
        url=url,
        health_score=results.get("health_score", 0),
        technical_score=results.get("technical", {}).get("score", 0),
        content_score=results.get("content", {}).get("score", 0),
        onpage_score=results.get("onpage", {}).get("score", 0),
        schema_score=results.get("schema_markup", {}).get("score", 0),
        performance_score=results.get("performance", {}).get("score", 0),
        security_score=results.get("security", {}).get("score", 0),
        geo_score=results.get("geo_score", 0),
        site_type=results.get("site_type", "other"),
        results=results,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
    )
    db.add(audit_record)
    await db.commit()
    await db.refresh(audit_record)

    # Build response
    return AuditResponse(
        id=audit_record.id,
        url=url,
        status=AuditStatus.COMPLETED,
        created_at=audit_record.created_at,
        health_score=results.get("health_score", 0),
        site_type=results.get("site_type", "other"),
        technical=results.get("technical", {}),
        content=results.get("content", {}),
        onpage=results.get("onpage", {}),
        schema_markup=results.get("schema_markup", {}),
        performance=results.get("performance", {}),
        security=results.get("security", {}),
        geo=results.get("geo", {}),
        geo_score=results.get("geo_score", 0),
        issues=issues,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        recommendations=results.get("recommendations", []),
    )


@router.get("/{audit_id}", response_model=AuditResponse)
async def get_audit(audit_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a previously completed audit by its ID."""
    result = await db.execute(
        select(AuditResult).where(AuditResult.id == audit_id)
    )
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    stored = audit.results or {}

    return AuditResponse(
        id=audit.id,
        url=audit.url,
        status=AuditStatus.COMPLETED,
        created_at=audit.created_at,
        health_score=audit.health_score or 0,
        site_type=audit.site_type or "other",
        technical=stored.get("technical", {}),
        content=stored.get("content", {}),
        onpage=stored.get("onpage", {}),
        schema_markup=stored.get("schema_markup", {}),
        performance=stored.get("performance", {}),
        security=stored.get("security", {}),
        geo=stored.get("geo", {}),
        geo_score=stored.get("geo_score", 0),
        issues=stored.get("issues", []),
        critical_count=audit.critical_count,
        high_count=audit.high_count,
        medium_count=audit.medium_count,
        low_count=audit.low_count,
        recommendations=stored.get("recommendations", []),
    )

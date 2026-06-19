"""
History API Routes.

GET /api/history              — List all past audits
GET /api/history/url?url=...  — Get audit history for a specific URL
"""
from __future__ import annotations


from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditResult
from app.schemas import AuditHistoryItem

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[AuditHistoryItem])
async def list_audits(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all past audits, most recent first."""
    result = await db.execute(
        select(AuditResult)
        .order_by(desc(AuditResult.created_at))
        .limit(limit)
        .offset(offset)
    )
    audits = result.scalars().all()

    return [
        AuditHistoryItem(
            id=a.id,
            url=a.url,
            health_score=a.health_score or 0,
            site_type=a.site_type,
            created_at=a.created_at,
            critical_count=a.critical_count,
            high_count=a.high_count,
            medium_count=a.medium_count,
            low_count=a.low_count,
        )
        for a in audits
    ]


@router.get("/url", response_model=list[AuditHistoryItem])
async def get_url_history(
    url: str = Query(..., description="URL to get history for"),
    db: AsyncSession = Depends(get_db),
):
    """Get audit history for a specific URL (drift comparison)."""
    result = await db.execute(
        select(AuditResult)
        .where(AuditResult.url == url)
        .order_by(desc(AuditResult.created_at))
        .limit(20)
    )
    audits = result.scalars().all()

    return [
        AuditHistoryItem(
            id=a.id,
            url=a.url,
            health_score=a.health_score or 0,
            site_type=a.site_type,
            created_at=a.created_at,
            critical_count=a.critical_count,
            high_count=a.high_count,
            medium_count=a.medium_count,
            low_count=a.low_count,
        )
        for a in audits
    ]

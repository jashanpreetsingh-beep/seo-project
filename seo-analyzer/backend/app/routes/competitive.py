"""
Competitive Gap Analysis API Routes.

POST /api/competitive/gap — Run full competitive content gap analysis pipeline
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/competitive", tags=["competitive"])


class GapAnalysisRequest(BaseModel):
    """Request body for competitive gap analysis."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Topic or keyword to analyze (e.g., 'RTO registration process')",
    )
    my_url: str = Field(
        ...,
        description="Your site URL (must have been previously audited to have embeddings)",
    )
    competitor_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Competitor page URLs to compare against (max 5)",
    )
    n_results: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Number of content chunks to analyze per source",
    )


class GapAnalysisResponse(BaseModel):
    """Response from the competitive gap analysis pipeline."""
    query: str
    my_url: str
    competitor_urls: list[str]
    comparison: dict
    gaps: list[dict]
    reranked_results: list[dict]
    competitor_details: dict
    recommendations: list[dict]
    summary: dict


@router.post("/gap", response_model=GapAnalysisResponse)
async def run_gap_analysis(request: GapAnalysisRequest):
    """
    Run the full competitive content gap analysis pipeline.

    Flow:
    1. Embed your query (local, sentence-transformers)
    2. Search your site's stored content (ChromaDB)
    3. Fetch & search competitor pages (live)
    4. Rerank all results (cross-encoder)
    5. Generate side-by-side comparison
    6. Detect content gaps (what they have, you don't)
    7. Generate actionable recommendations (LLM)

    Prerequisites:
    - Your site URL must have been previously audited (POST /api/audit)
      so its content is stored in the vector database.
    - Competitor URLs are fetched live (no prior audit needed).
    """
    try:
        from app.competitive_gap import run_competitive_gap_analysis
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Competitive analysis not available (missing dependency): {e}",
        )

    try:
        result = await run_competitive_gap_analysis(
            query=request.query,
            my_url=request.my_url,
            competitor_urls=request.competitor_urls,
            n_results=request.n_results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(e)}")

    return GapAnalysisResponse(**result)

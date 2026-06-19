"""
AI Visibility Checker API Route.

POST /api/visibility  — Run an AI visibility check
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.visibility_workflow import run_visibility_check

router = APIRouter(prefix="/api/visibility", tags=["visibility"])


# ─── Request / Response Schemas ───────────────────────────────────────────────

class VisibilityRequest(BaseModel):
    """Request to run an AI visibility check."""
    query: str = Field(..., description="Search query to simulate", min_length=2, max_length=500)
    target_url: str = Field(..., description="Your URL to check rank for")
    provider: str = Field(default="groq", description="LLM provider: 'groq' or 'anthropic'")
    num_results: int = Field(default=30, ge=5, le=30, description="Number of results to request")


class VisibilityResult(BaseModel):
    """Single result entry."""
    rank: int
    url: str
    reason: str = ""
    valid: bool = False


class TokenUsageResponse(BaseModel):
    """Token usage info."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""


class VisibilityResponse(BaseModel):
    """Complete visibility check response."""
    query: str
    target_url: str
    provider: str
    model: str = ""
    results: List[VisibilityResult] = []
    target_found: bool = False
    target_rank: Optional[int] = None
    match_type: str = "not_found"  # "exact" | "domain" | "not_found"
    total_valid_results: int = 0
    competitors_above: List[str] = []
    token_usage: Optional[TokenUsageResponse] = None
    error: Optional[str] = None


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("", response_model=VisibilityResponse)
async def check_visibility(request: VisibilityRequest):
    """
    Run an AI visibility check.

    Asks the selected LLM what websites it would recommend for a query,
    validates that those URLs actually exist, and checks if your target
    URL appears in the rankings.

    Takes 10-30 seconds depending on URL validation.
    """
    # Normalize target URL
    target_url = request.target_url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    try:
        results = await run_visibility_check(
            query=request.query.strip(),
            target_url=target_url,
            provider=request.provider,
            num_results=request.num_results,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visibility check failed: {str(e)}")

    return VisibilityResponse(**results)

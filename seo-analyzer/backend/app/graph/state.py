"""
LangGraph State Definition.

The state flows through the graph, accumulating results from each analyzer node.
This is the shared "blackboard" that all nodes read from and write to.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class SEOState(TypedDict):
    """
    Shared state passed between all LangGraph nodes.
    
    Flow:
    1. `fetch` node populates: url, html, status_code, headers, redirect_chain
    2. Analyzer nodes read html/headers and write their results
    3. `scorer` node reads all results and computes health_score
    4. GEO agents analyze AI visibility signals
    5. GEO scorer/improvement/report nodes compile the GEO strategy
    """

    # ─── Input ────────────────────────────────────────────────────────────────
    url: str  # The target URL to analyze

    # ─── Fetch Results (populated by fetch_page node) ─────────────────────────
    html: str  # Raw HTML content
    status_code: int  # HTTP status code
    headers: Dict[str, str]  # Response headers
    redirect_chain: List[dict]  # List of redirects encountered
    fetch_error: Optional[str]  # Error message if fetch failed

    # ─── SEO Analysis Results (populated by each analyzer node) ───────────────
    technical_result: Optional[dict]
    content_result: Optional[dict]
    onpage_result: Optional[dict]
    schema_result: Optional[dict]
    performance_result: Optional[dict]
    security_result: Optional[dict]

    # ─── SEO Final Output (populated by scorer node) ──────────────────────────
    health_score: float
    site_type: str
    issues: List[dict]
    recommendations: List[dict]

    # ─── GEO Agent Results (5 analysis agents) ────────────────────────────────
    geo_entity_result: Optional[dict]       # Entity Understanding Agent
    geo_answer_result: Optional[dict]       # Answer Extraction Agent
    geo_authority_result: Optional[dict]    # Authority & Trust Agent
    geo_citation_result: Optional[dict]     # Citation Probability Agent
    geo_conversational_result: Optional[dict]  # Conversational Search Agent

    # ─── GEO Scoring & Strategy ───────────────────────────────────────────────
    geo_score: float                        # Overall GEO score (0-100)
    geo_scores: Optional[dict]              # Individual component scores
    geo_visibility: Optional[dict]          # AI visibility level
    geo_strengths: Optional[List[dict]]     # Strong areas
    geo_weaknesses: Optional[List[dict]]    # Weak areas
    geo_all_issues: Optional[List[dict]]    # All GEO issues aggregated
    geo_priority_actions: Optional[List[dict]]  # Prioritized improvements
    geo_potential_score: float              # Score after improvements
    geo_total_potential_gain: float         # Total possible gain
    geo_report: Optional[dict]             # Final compiled GEO report

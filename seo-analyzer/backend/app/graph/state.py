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
    """

    # ─── Input ────────────────────────────────────────────────────────────────
    url: str  # The target URL to analyze

    # ─── Fetch Results (populated by fetch_page node) ─────────────────────────
    html: str  # Raw HTML content
    status_code: int  # HTTP status code
    headers: Dict[str, str]  # Response headers
    redirect_chain: List[dict]  # List of redirects encountered
    fetch_error: Optional[str]  # Error message if fetch failed

    # ─── Analysis Results (populated by each analyzer node) ───────────────────
    technical_result: Optional[dict]
    content_result: Optional[dict]
    onpage_result: Optional[dict]
    schema_result: Optional[dict]
    performance_result: Optional[dict]
    security_result: Optional[dict]

    # ─── Final Output (populated by scorer node) ──────────────────────────────
    health_score: float
    site_type: str
    issues: List[dict]
    recommendations: List[dict]

    # ─── Token Usage (populated by llm_recommendations node) ──────────────────
    token_usage: Optional[dict]  # {input_tokens, output_tokens, total_tokens, model}

"""
AI Visibility Checker - LangGraph State Definition.

State flows through the graph:
1. query_llm → asks LLM for top N URLs for a query
2. validate_urls → checks which URLs actually exist
3. rank_checker → finds target URL in the list
4. build_report → generates final summary
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class VisibilityState(TypedDict):
    """Shared state for the AI visibility checker workflow."""

    # ─── Input ────────────────────────────────────────────────────────────────
    query: str          # The search query (e.g., "best CRM software")
    target_url: str     # The URL to check rank for
    provider: str       # "groq" or "anthropic"
    num_results: int    # How many results to request (max 30)

    # ─── LLM Query Results ────────────────────────────────────────────────────
    raw_results: List[Dict]     # Raw LLM output: [{rank, url, reason}, ...]
    llm_error: Optional[str]    # Error if LLM call failed

    # ─── Validation Results ───────────────────────────────────────────────────
    validated_results: List[Dict]  # Results with 'valid' field added

    # ─── Rank Check Results ───────────────────────────────────────────────────
    target_found: bool
    target_rank: Optional[int]
    match_type: Optional[str]       # "exact" | "domain" | "not_found"
    competitors_above: List[str]    # Domains ranked above target

    # ─── Final Report ─────────────────────────────────────────────────────────
    total_valid_results: int
    token_usage: Optional[Dict]
    model_used: str

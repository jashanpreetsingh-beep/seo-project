"""
GEO Scorer Node - Computes the final weighted GEO score.

GEO Score Calculation:
  Entity Understanding:    25%
  Answer Extraction:       25%
  Authority & Trust:       20%
  Citation Probability:    15%
  Conversational Search:   15%
  ─────────────────────────────
  Total GEO Score:        100%
"""
from __future__ import annotations

from app.graph.state import SEOState


# GEO scoring weights (must sum to 1.0)
GEO_WEIGHTS = {
    "entity": 0.25,
    "answer": 0.25,
    "authority": 0.20,
    "citation": 0.15,
    "conversational": 0.15,
}

# AI Visibility level thresholds
VISIBILITY_LEVELS = [
    (90, "Excellent", "Your site is highly optimized for AI search engines"),
    (75, "Strong", "AI can understand and recommend your site effectively"),
    (60, "Moderate", "AI has partial understanding — significant room for improvement"),
    (40, "Weak", "AI struggles to understand or recommend your site"),
    (0, "Poor", "Your site is nearly invisible to AI search engines"),
]


def _get_visibility_level(score: float) -> dict:
    """Determine AI visibility level from score."""
    for threshold, level, description in VISIBILITY_LEVELS:
        if score >= threshold:
            return {
                "level": level,
                "description": description,
                "threshold": threshold,
            }
    return {"level": "Poor", "description": "Critical GEO issues", "threshold": 0}


def _identify_strengths_weaknesses(scores: dict) -> tuple[list, list]:
    """Identify top strengths and weaknesses from component scores."""
    labels = {
        "entity": "Entity Understanding",
        "answer": "Answer Extraction",
        "authority": "Authority & Trust",
        "citation": "Citation Probability",
        "conversational": "Conversational Search",
    }

    strengths = []
    weaknesses = []

    for key, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        label = labels.get(key, key)
        if score >= 60:
            strengths.append({"category": label, "score": score})
        else:
            weaknesses.append({"category": label, "score": score})

    return strengths, weaknesses


async def geo_scorer_node(state: SEOState) -> dict:
    """
    Compute the weighted GEO score from all 5 agent results.
    """
    # Get individual scores
    entity_result = state.get("geo_entity_result", {}) or {}
    answer_result = state.get("geo_answer_result", {}) or {}
    authority_result = state.get("geo_authority_result", {}) or {}
    citation_result = state.get("geo_citation_result", {}) or {}
    conversational_result = state.get("geo_conversational_result", {}) or {}

    scores = {
        "entity": entity_result.get("score", 0),
        "answer": answer_result.get("score", 0),
        "authority": authority_result.get("score", 0),
        "citation": citation_result.get("score", 0),
        "conversational": conversational_result.get("score", 0),
    }

    # Calculate weighted GEO score
    geo_score = sum(scores[k] * GEO_WEIGHTS[k] for k in GEO_WEIGHTS)
    geo_score = round(min(100, max(0, geo_score)), 1)

    # Get visibility level
    visibility = _get_visibility_level(geo_score)

    # Identify strengths and weaknesses
    strengths, weaknesses = _identify_strengths_weaknesses(scores)

    # Aggregate all issues from all agents
    all_issues = []
    for result in [entity_result, answer_result, authority_result, citation_result, conversational_result]:
        all_issues.extend(result.get("issues", []))

    # Sort issues by estimated impact (parse "+X GEO points" from impact string)
    def _parse_impact(issue):
        import re
        match = re.search(r'\+(\d+)', issue.get("impact", ""))
        return int(match.group(1)) if match else 0

    all_issues.sort(key=_parse_impact, reverse=True)

    return {
        "geo_score": geo_score,
        "geo_scores": scores,
        "geo_visibility": visibility,
        "geo_strengths": strengths,
        "geo_weaknesses": weaknesses,
        "geo_all_issues": all_issues,
    }

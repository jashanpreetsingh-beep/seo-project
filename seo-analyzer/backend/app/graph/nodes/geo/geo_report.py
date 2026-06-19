"""
GEO Report Agent - Produces the final GEO strategy report with 90-day plan.

This is the final node that compiles all GEO analysis into a comprehensive
report including:
- Current GEO Score breakdown
- AI Visibility Level
- Strengths & Weaknesses
- Priority Actions
- 90-Day GEO Improvement Plan
- Expected outcomes
"""
from __future__ import annotations

from app.graph.state import SEOState


def _generate_90_day_plan(
    scores: dict,
    priority_actions: list,
    geo_score: float,
) -> dict:
    """Generate a 3-month GEO improvement roadmap."""
    plan = {
        "month_1": {
            "title": "Foundation — Fix Entity & Structure",
            "focus": "Establish clear identity and content structure for AI",
            "tasks": [],
            "expected_gain": 0,
        },
        "month_2": {
            "title": "Authority — Build Trust & Content",
            "focus": "Create authoritative content AI wants to cite",
            "tasks": [],
            "expected_gain": 0,
        },
        "month_3": {
            "title": "Dominance — Original Research & Coverage",
            "focus": "Produce citation-worthy content and expand coverage",
            "tasks": [],
            "expected_gain": 0,
        },
    }

    # Assign actions to months based on effort and priority
    import re
    for action in priority_actions:
        effort = action.get("effort", "").lower()
        category = action.get("category", "").lower()
        gain_match = re.search(r'\+(\d+)', action.get("estimated_score_gain", ""))
        gain = int(gain_match.group(1)) if gain_match else 3

        # Month 1: Entity, structure, low-effort fixes
        if "entity" in category or "low" in effort:
            plan["month_1"]["tasks"].append(action.get("solution", action.get("issue", "")))
            plan["month_1"]["expected_gain"] += gain
        # Month 2: Authority, trust, medium-effort
        elif "authority" in category or "answer" in category:
            plan["month_2"]["tasks"].append(action.get("solution", action.get("issue", "")))
            plan["month_2"]["expected_gain"] += gain
        # Month 3: Citation, research, high-effort
        else:
            plan["month_3"]["tasks"].append(action.get("solution", action.get("issue", "")))
            plan["month_3"]["expected_gain"] += gain

    # Ensure each month has at least some tasks
    if not plan["month_1"]["tasks"]:
        plan["month_1"]["tasks"] = [
            "Audit and clarify entity identity across all pages",
            "Add structured data (Organization, FAQ schema)",
            "Create clear about/team pages with credentials",
        ]
        plan["month_1"]["expected_gain"] = 10

    if not plan["month_2"]["tasks"]:
        plan["month_2"]["tasks"] = [
            "Publish expert content with author profiles",
            "Create FAQ pages for common questions",
            "Add testimonials and case studies",
        ]
        plan["month_2"]["expected_gain"] = 12

    if not plan["month_3"]["tasks"]:
        plan["month_3"]["tasks"] = [
            "Publish original research with data",
            "Create comprehensive comparison guides",
            "Build external authority signals",
        ]
        plan["month_3"]["expected_gain"] = 15

    # Limit tasks per month
    for month in plan.values():
        month["tasks"] = month["tasks"][:5]

    return plan


async def geo_report_node(state: SEOState) -> dict:
    """
    Compile the final GEO report from all analysis data.
    """
    geo_score = state.get("geo_score", 0)
    scores = state.get("geo_scores", {})
    visibility = state.get("geo_visibility", {})
    strengths = state.get("geo_strengths", [])
    weaknesses = state.get("geo_weaknesses", [])
    priority_actions = state.get("geo_priority_actions", [])
    potential_score = state.get("geo_potential_score", 0)
    total_potential_gain = state.get("geo_total_potential_gain", 0)

    # Individual agent results
    entity_result = state.get("geo_entity_result", {}) or {}
    answer_result = state.get("geo_answer_result", {}) or {}
    authority_result = state.get("geo_authority_result", {}) or {}
    citation_result = state.get("geo_citation_result", {}) or {}
    conversational_result = state.get("geo_conversational_result", {}) or {}

    # Generate 90-day plan
    plan_90_day = _generate_90_day_plan(scores, priority_actions, geo_score)

    # Compile final report
    geo_report = {
        "geo_score": geo_score,
        "visibility": visibility,
        "scores": {
            "entity_understanding": {
                "score": scores.get("entity", 0),
                "weight": "25%",
                "label": "Entity Understanding",
                "detail": entity_result,
            },
            "answer_extraction": {
                "score": scores.get("answer", 0),
                "weight": "25%",
                "label": "Answer Extraction",
                "detail": answer_result,
            },
            "authority_trust": {
                "score": scores.get("authority", 0),
                "weight": "20%",
                "label": "Authority & Trust",
                "detail": authority_result,
            },
            "citation_probability": {
                "score": scores.get("citation", 0),
                "weight": "15%",
                "label": "Citation Probability",
                "detail": citation_result,
            },
            "conversational_search": {
                "score": scores.get("conversational", 0),
                "weight": "15%",
                "label": "Conversational Search",
                "detail": conversational_result,
            },
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "priority_actions": priority_actions,
        "potential_score": potential_score,
        "total_potential_gain": total_potential_gain,
        "plan_90_day": plan_90_day,
    }

    return {
        "geo_report": geo_report,
    }

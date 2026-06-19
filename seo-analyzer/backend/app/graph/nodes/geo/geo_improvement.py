"""
GEO Improvement Agent - Generates prioritized improvement actions.

After scoring, this agent takes the weaknesses and generates
a prioritized action plan with expected GEO impact for each fix.
"""
from __future__ import annotations

from app.graph.state import SEOState


def _generate_priority_actions(
    geo_score: float,
    scores: dict,
    weaknesses: list,
    all_issues: list,
) -> list[dict]:
    """Generate prioritized improvement actions based on analysis."""
    actions = []
    priority = 1

    # Priority actions derived from worst-scoring categories
    category_actions = {
        "entity": {
            "low_actions": [
                {
                    "issue": "AI cannot understand your business identity",
                    "solution": "Create a clear entity statement on homepage: '[Company] is a [location]-based [industry] company helping [audience] achieve [outcome] through [method]'",
                    "impact": "High",
                    "estimated_score_gain": "+12 GEO",
                    "effort": "Low (1-2 hours)",
                    "category": "Entity Understanding",
                },
                {
                    "issue": "Services/products not explicitly defined",
                    "solution": "Create dedicated service/product pages with clear descriptions, pricing, and use cases AI can parse",
                    "impact": "High",
                    "estimated_score_gain": "+8 GEO",
                    "effort": "Medium (4-8 hours)",
                    "category": "Entity Understanding",
                },
            ],
        },
        "answer": {
            "low_actions": [
                {
                    "issue": "AI cannot extract direct answers from your content",
                    "solution": "Add comprehensive FAQ section with 10-20 questions your audience commonly asks. Use H2/H3 question headings with direct paragraph answers",
                    "impact": "High",
                    "estimated_score_gain": "+10 GEO",
                    "effort": "Medium (3-5 hours)",
                    "category": "Answer Extraction",
                },
                {
                    "issue": "Content lacks structured data for AI parsing",
                    "solution": "Add FAQ schema markup, create how-to guides with numbered steps, add comparison tables",
                    "impact": "Medium",
                    "estimated_score_gain": "+7 GEO",
                    "effort": "Medium (4-6 hours)",
                    "category": "Answer Extraction",
                },
            ],
        },
        "authority": {
            "low_actions": [
                {
                    "issue": "AI cannot verify your expertise or authority",
                    "solution": "Create detailed author/team profiles: full name, photo, credentials, years of experience, publications, certifications",
                    "impact": "High",
                    "estimated_score_gain": "+10 GEO",
                    "effort": "Low (2-3 hours)",
                    "category": "Authority & Trust",
                },
                {
                    "issue": "No social proof for AI to reference",
                    "solution": "Add testimonials with full names and companies, case studies with measurable results, aggregate review ratings",
                    "impact": "Medium",
                    "estimated_score_gain": "+7 GEO",
                    "effort": "Medium (5-8 hours)",
                    "category": "Authority & Trust",
                },
            ],
        },
        "citation": {
            "low_actions": [
                {
                    "issue": "Low citation probability — nothing unique for AI to reference",
                    "solution": "Publish original research: analyze your industry data, create benchmarks, run surveys, share proprietary insights with specific numbers",
                    "impact": "Very High",
                    "estimated_score_gain": "+15 GEO",
                    "effort": "High (10-20 hours)",
                    "category": "Citation Probability",
                },
                {
                    "issue": "Content lacks specific data and statistics",
                    "solution": "Add quantified claims with sources: '32% improvement', 'based on 500 client projects', 'reduced costs by $2M'",
                    "impact": "Medium",
                    "estimated_score_gain": "+8 GEO",
                    "effort": "Low (2-4 hours)",
                    "category": "Citation Probability",
                },
            ],
        },
        "conversational": {
            "low_actions": [
                {
                    "issue": "Content doesn't match how users query AI",
                    "solution": "Rewrite content with question-based headings that match natural language: 'How much does X cost?', 'What is the best Y for Z?'",
                    "impact": "Medium",
                    "estimated_score_gain": "+6 GEO",
                    "effort": "Medium (3-5 hours)",
                    "category": "Conversational Search",
                },
                {
                    "issue": "Missing comparison and 'best of' content",
                    "solution": "Create comparison pages (Your Product vs Competitors), cost guides, and 'best X for Y' articles",
                    "impact": "Medium",
                    "estimated_score_gain": "+8 GEO",
                    "effort": "Medium (5-8 hours)",
                    "category": "Conversational Search",
                },
            ],
        },
    }

    # Add actions for weak categories (score < 50)
    for weakness in weaknesses:
        category_key = None
        for key in category_actions:
            if key in weakness["category"].lower():
                category_key = key
                break

        if category_key and scores.get(category_key, 0) < 50:
            for action in category_actions[category_key]["low_actions"]:
                action["priority"] = priority
                actions.append(action)
                priority += 1

    # Add top issues as actions if not already covered
    covered_issues = {a["issue"] for a in actions}
    for issue in all_issues[:5]:
        if issue.get("issue") not in covered_issues:
            actions.append({
                "priority": priority,
                "issue": issue.get("issue", ""),
                "solution": issue.get("suggestion", ""),
                "impact": "Medium",
                "estimated_score_gain": issue.get("impact", "+5 GEO"),
                "effort": "Medium",
                "category": issue.get("signal", "General"),
            })
            priority += 1

    # Sort by estimated score gain
    def _parse_gain(action):
        import re
        match = re.search(r'\+(\d+)', action.get("estimated_score_gain", ""))
        return int(match.group(1)) if match else 0

    actions.sort(key=_parse_gain, reverse=True)

    # Re-assign priorities after sorting
    for i, action in enumerate(actions):
        action["priority"] = i + 1

    return actions[:10]  # Top 10 actions


async def geo_improvement_node(state: SEOState) -> dict:
    """
    Generate prioritized GEO improvement actions.
    """
    geo_score = state.get("geo_score", 0)
    scores = state.get("geo_scores", {})
    weaknesses = state.get("geo_weaknesses", [])
    all_issues = state.get("geo_all_issues", [])

    priority_actions = _generate_priority_actions(
        geo_score, scores, weaknesses, all_issues
    )

    # Calculate potential score after improvements
    import re
    total_potential_gain = 0
    for action in priority_actions[:5]:  # Top 5 realistically achievable
        match = re.search(r'\+(\d+)', action.get("estimated_score_gain", ""))
        if match:
            total_potential_gain += int(match.group(1))

    potential_score = min(100, geo_score + total_potential_gain)

    return {
        "geo_priority_actions": priority_actions,
        "geo_potential_score": potential_score,
        "geo_total_potential_gain": total_potential_gain,
    }

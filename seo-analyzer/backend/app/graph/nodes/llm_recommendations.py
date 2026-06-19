"""
LLM Recommendations Node - Uses Claude Sonnet to generate smart SEO advice.

This node takes all the raw analysis results and asks Claude to:
1. Synthesize findings into a coherent strategy
2. Prioritize actions based on impact and effort
3. Provide specific, actionable recommendations (not generic advice)
4. Detect patterns across categories (e.g., content issues + schema gaps = topical authority problem)

This is OPTIONAL — the scorer node already generates rule-based recommendations.
The LLM node adds AI intelligence on top for more nuanced, contextual advice.
"""

from app.config import settings
from app.graph.state import SEOState


async def llm_recommendations_node(state: SEOState) -> dict:
    """
    Use Claude Sonnet 4 to generate intelligent SEO recommendations.
    
    Only runs if ANTHROPIC_API_KEY is configured.
    Falls back gracefully if not available.
    """
    if not settings.ANTHROPIC_API_KEY:
        # No API key — skip LLM analysis, use rule-based recommendations only
        return {}

    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        # Initialize Claude with user's config (supports custom proxy)
        llm_kwargs = {
            "model": settings.ANTHROPIC_MODEL,
            "anthropic_api_key": settings.ANTHROPIC_API_KEY,
            "max_tokens": 2000,
            "temperature": 0.3,  # Low temp for factual, precise recommendations
        }
        # Use custom base URL if configured (for proxy setups)
        if settings.ANTHROPIC_BASE_URL:
            llm_kwargs["anthropic_api_url"] = settings.ANTHROPIC_BASE_URL

        llm = ChatAnthropic(**llm_kwargs)

        # Collect all issues from analyzers
        all_issues = state.get("issues", [])
        technical = state.get("technical_result", {}) or {}
        content = state.get("content_result", {}) or {}
        performance = state.get("performance_result", {}) or {}
        onpage = state.get("onpage_result", {}) or {}
        schema = state.get("schema_result", {}) or {}
        security = state.get("security_result", {}) or {}
        site_type = state.get("site_type", "other")
        health_score = state.get("health_score", 0)

        # Build context for Claude
        issues_summary = "\n".join(
            f"- [{i.get('severity', 'medium').upper()}] {i.get('title', '')}: {i.get('description', '')}"
            for i in all_issues[:15]  # Cap at 15 to stay within token limits
        )

        scores_summary = f"""
        Technical: {technical.get('score', 0)}/100
        Content: {content.get('score', 0)}/100
        On-Page: {onpage.get('score', 0)}/100
        Schema: {schema.get('score', 0)}/100
        Performance: {performance.get('score', 0)}/100
        Security: {security.get('score', 0)}/100
        Overall Health: {health_score}/100
        """

        prompt = f"""You are an expert SEO consultant. Based on this audit data, provide 5-7 prioritized recommendations.

URL: {state.get('url', '')}
Site Type: {site_type}
Health Score: {health_score}/100

Category Scores:
{scores_summary}

Issues Found:
{issues_summary}

Additional Context:
- Word count: {content.get('word_count', 'unknown')}
- Has canonical: {technical.get('canonicals', {}).get('has_canonical', 'unknown')}
- Has sitemap: {technical.get('sitemap', {}).get('found', 'unknown')}
- Schema types found: {[s.get('type') for s in schema.get('schemas_found', [])]}
- Performance source: {performance.get('source', 'unknown')}

Rules:
- Be specific to THIS site, not generic advice
- Each recommendation must have: action, why it matters, expected impact, and estimated effort (hours)
- Consider dependencies (what must be done first)
- For a {site_type} site, prioritize accordingly
- Never recommend deprecated schema (HowTo deprecated Sept 2023, FAQ rich results retired May 2026)
- Core Web Vitals: use INP (not FID — FID was removed Sept 2024)
- Format as JSON array

Respond ONLY with a JSON array like:
[
  {{
    "priority": 1,
    "action": "specific action to take",
    "why": "why this matters for rankings",
    "impact": "high/medium/low",
    "effort_hours": 2,
    "category": "technical/content/performance/schema/security/onpage",
    "depends_on": []
  }}
]"""

        messages = [
            SystemMessage(content="You are a senior SEO consultant. Return only valid JSON. No markdown formatting, no code blocks, just the raw JSON array."),
            HumanMessage(content=prompt),
        ]

        response = await llm.ainvoke(messages)

        # Parse Claude's response
        import json
        try:
            recommendations = json.loads(response.content)
            if isinstance(recommendations, list):
                return {"recommendations": recommendations}
        except json.JSONDecodeError:
            # If Claude didn't return valid JSON, fall back
            pass

    except ImportError:
        # langchain-anthropic not installed
        pass
    except Exception as e:
        # Any error — log and continue with rule-based recommendations
        print(f"LLM recommendations failed (non-fatal): {e}")

    return {}

"""
LLM Recommendations Node - Uses Claude or Groq to generate smart SEO advice.

Supports multiple LLM providers via the LLM_PROVIDER config:
- "groq"      → Groq API (free tier, fast inference, Llama models)
- "anthropic" → Anthropic Claude API (paid, highest quality)

Switch providers by changing LLM_PROVIDER in .env. Token usage is tracked
regardless of which provider is active.
"""

from __future__ import annotations

import json
from typing import List, Dict, Optional, Tuple

from app.config import settings
from app.graph.state import SEOState


def _build_prompt(state: SEOState) -> str:
    """Build the SEO recommendation prompt from audit state."""
    all_issues = state.get("issues", [])
    technical = state.get("technical_result", {}) or {}
    content = state.get("content_result", {}) or {}
    performance = state.get("performance_result", {}) or {}
    onpage = state.get("onpage_result", {}) or {}
    schema = state.get("schema_result", {}) or {}
    security = state.get("security_result", {}) or {}
    site_type = state.get("site_type", "other")
    health_score = state.get("health_score", 0)

    issues_summary = "\n".join(
        f"- [{i.get('severity', 'medium').upper()}] {i.get('title', '')}: {i.get('description', '')}"
        for i in all_issues[:15]
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

    return f"""You are an expert SEO consultant. Based on this audit data, provide 5-7 prioritized recommendations.

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


SYSTEM_MESSAGE = "You are a senior SEO consultant. Return only valid JSON. No markdown formatting, no code blocks, just the raw JSON array."


async def _call_anthropic(prompt: str) -> Tuple[Optional[List], Optional[Dict]]:
    """Call Anthropic Claude API. Returns (recommendations, token_usage)."""
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    llm_kwargs = {
        "model": settings.ANTHROPIC_MODEL,
        "anthropic_api_key": settings.ANTHROPIC_API_KEY,
        "max_tokens": 2000,
        "temperature": 0.3,
    }
    if settings.ANTHROPIC_BASE_URL:
        llm_kwargs["anthropic_api_url"] = settings.ANTHROPIC_BASE_URL

    llm = ChatAnthropic(**llm_kwargs)

    messages = [
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)

    # Extract token usage
    token_usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
        token_usage = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": settings.ANTHROPIC_MODEL,
            "provider": "anthropic",
        }

    # Parse response
    try:
        recommendations = json.loads(response.content)
        if isinstance(recommendations, list):
            return recommendations, token_usage
    except json.JSONDecodeError:
        pass

    return None, token_usage


async def _call_groq(prompt: str) -> Tuple[Optional[List], Optional[Dict]]:
    """Call Groq API. Returns (recommendations, token_usage)."""
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        max_tokens=2000,
        temperature=0.3,
    )

    messages = [
        SystemMessage(content=SYSTEM_MESSAGE),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)

    # Extract token usage
    token_usage = None
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
        token_usage = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": settings.GROQ_MODEL,
            "provider": "groq",
        }

    # Parse response
    try:
        recommendations = json.loads(response.content)
        if isinstance(recommendations, list):
            return recommendations, token_usage
    except json.JSONDecodeError:
        pass

    return None, token_usage


async def llm_recommendations_node(state: SEOState) -> dict:
    """
    Generate LLM-powered SEO recommendations using the configured provider.

    Provider is selected via LLM_PROVIDER env var:
    - "groq"      → Free, fast (Llama 3.3 70B)
    - "anthropic" → Paid, highest quality (Claude Sonnet 4)

    Falls back gracefully if no API key is configured.
    """
    provider = settings.LLM_PROVIDER.lower()

    # Check if the selected provider has an API key
    if provider == "anthropic" and not settings.ANTHROPIC_API_KEY:
        return {}
    if provider == "groq" and not settings.GROQ_API_KEY:
        return {}

    try:
        prompt = _build_prompt(state)

        if provider == "anthropic":
            recommendations, token_usage = await _call_anthropic(prompt)
        elif provider == "groq":
            recommendations, token_usage = await _call_groq(prompt)
        else:
            print(f"Unknown LLM_PROVIDER: {provider}. Use 'groq' or 'anthropic'.")
            return {}

        result = {}
        if recommendations:
            result["recommendations"] = recommendations
        if token_usage:
            result["token_usage"] = token_usage
        return result

    except ImportError as e:
        print(f"LLM provider '{provider}' package not installed: {e}")
    except Exception as e:
        print(f"LLM recommendations failed (non-fatal): {e}")

    return {}

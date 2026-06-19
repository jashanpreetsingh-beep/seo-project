"""
AI Visibility Checker - LangGraph Workflow.

Graph structure:
    START → query_llm → validate_urls → rank_checker → END

Asks an LLM "what are the top N websites for [query]?" then checks
if the target URL appears in the results and at what rank.
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from langgraph.graph import StateGraph, END

from app.config import settings
from app.graph.visibility_state import VisibilityState


# ─── Node 1: Query the LLM ───────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a search engine simulation. When given a query, return the most relevant real websites that would rank for this query. Be honest and accurate — only return real, existing websites that are genuinely relevant.

Rules:
- Return ONLY real, existing websites with valid URLs
- Include the full URL (with https://)
- Rank them by relevance and authority
- Give a brief reason why each site ranks where it does
- Do NOT invent or hallucinate URLs
- Do NOT include generic examples like example.com
- Return ONLY valid JSON, no markdown, no code blocks"""


def _build_query_prompt(query: str, num_results: int) -> str:
    return f"""For the search query: "{query}"

List the top {num_results} most relevant and authoritative websites that would appear in search results. Return real, existing URLs only.

Respond with ONLY a JSON array (no markdown, no explanation):
[
  {{"rank": 1, "url": "https://...", "reason": "brief reason"}},
  {{"rank": 2, "url": "https://...", "reason": "brief reason"}}
]"""


async def _call_llm(provider: str, prompt: str) -> Tuple[Optional[str], Optional[Dict]]:
    """Call the selected LLM provider. Returns (response_text, token_usage)."""
    from langchain_core.messages import HumanMessage, SystemMessage

    token_usage = None

    if provider == "groq":
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            max_tokens=4000,
            temperature=0.2,
        )
        model_name = settings.GROQ_MODEL
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        llm_kwargs = {
            "model": settings.ANTHROPIC_MODEL,
            "anthropic_api_key": settings.ANTHROPIC_API_KEY,
            "max_tokens": 4000,
            "temperature": 0.2,
        }
        if settings.ANTHROPIC_BASE_URL:
            llm_kwargs["anthropic_api_url"] = settings.ANTHROPIC_BASE_URL
        llm = ChatAnthropic(**llm_kwargs)
        model_name = settings.ANTHROPIC_MODEL
    else:
        return None, None

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = response.usage_metadata
        token_usage = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "model": model_name,
            "provider": provider,
        }

    return response.content, token_usage


async def query_llm_node(state: VisibilityState) -> dict:
    """Ask the LLM for top N websites for the given query."""
    query = state["query"]
    provider = state["provider"]
    num_results = state["num_results"]

    prompt = _build_query_prompt(query, num_results)

    try:
        response_text, token_usage = await _call_llm(provider, prompt)

        if not response_text:
            return {"raw_results": [], "llm_error": "Empty response from LLM", "token_usage": token_usage}

        # Clean response — strip markdown code blocks if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        results = json.loads(cleaned)

        if not isinstance(results, list):
            return {"raw_results": [], "llm_error": "LLM did not return a list", "token_usage": token_usage}

        # Normalize results
        normalized = []
        for i, item in enumerate(results):
            if isinstance(item, dict) and "url" in item:
                normalized.append({
                    "rank": item.get("rank", i + 1),
                    "url": item["url"].strip(),
                    "reason": item.get("reason", ""),
                })

        model_name = settings.GROQ_MODEL if provider == "groq" else settings.ANTHROPIC_MODEL
        return {
            "raw_results": normalized,
            "llm_error": None,
            "token_usage": token_usage,
            "model_used": model_name,
        }

    except json.JSONDecodeError as e:
        return {"raw_results": [], "llm_error": f"Failed to parse LLM response as JSON: {str(e)}"}
    except Exception as e:
        return {"raw_results": [], "llm_error": f"LLM call failed: {str(e)}"}


# ─── Node 2: Validate URLs ───────────────────────────────────────────────────

async def validate_urls_node(state: VisibilityState) -> dict:
    """Check which URLs actually exist via HTTP HEAD requests."""
    raw_results = state.get("raw_results", [])

    if not raw_results:
        return {"validated_results": [], "total_valid_results": 0}

    validated = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0),
        follow_redirects=True,
        verify=False,  # Some sites have cert issues
    ) as client:
        for item in raw_results:
            url = item.get("url", "")
            valid = False

            # Basic URL format check
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            try:
                parsed = urlparse(url)
                if parsed.netloc and "." in parsed.netloc:
                    resp = await client.head(url)
                    # Consider 2xx, 3xx, and even 403 (blocked but exists) as valid
                    valid = resp.status_code < 500
            except Exception:
                # URL doesn't resolve — mark as invalid
                valid = False

            validated.append({
                **item,
                "url": url,
                "valid": valid,
            })

    total_valid = sum(1 for v in validated if v["valid"])
    return {"validated_results": validated, "total_valid_results": total_valid}


# ─── Node 3: Rank Checker ────────────────────────────────────────────────────

def _normalize_domain(url: str) -> str:
    """Extract and normalize domain from URL."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url.lower()


def _domains_match(target_domain: str, item_domain: str) -> bool:
    """
    Smart domain matching that handles partial inputs.
    
    Examples:
      - "policybazaar" matches "policybazaar.com"
      - "policybazaar.com" matches "policybazaar.com"
      - "app.hubspot.com" matches "hubspot.com" (subdomain)
      - "hubspot" matches "hubspot.com"
    """
    if not target_domain or not item_domain:
        return False

    # Exact match
    if target_domain == item_domain:
        return True

    # Target without TLD matches item's base domain
    # e.g., "policybazaar" matches "policybazaar.com"
    item_base = item_domain.split(".")[0]  # "policybazaar" from "policybazaar.com"
    target_base = target_domain.split(".")[0]

    if target_base == item_base:
        return True

    # Target is contained in item domain or vice versa
    # e.g., "policybazaar" in "policybazaar.com" or "policybazaar.com" in "www.policybazaar.com"
    if target_domain in item_domain or item_domain in target_domain:
        return True

    return False


async def rank_checker_node(state: VisibilityState) -> dict:
    """Check if target URL appears in the validated results."""
    target_url = state["target_url"]
    validated = state.get("validated_results", [])

    target_domain = _normalize_domain(target_url)
    target_full = target_url.lower().rstrip("/")

    target_found = False
    target_rank = None
    match_type = "not_found"
    competitors_above = []

    for item in validated:
        item_url = item["url"].lower().rstrip("/")
        item_domain = _normalize_domain(item["url"])
        rank = item.get("rank", 0)

        # Check for exact URL match
        if item_url == target_full or item_url == target_full + "/":
            target_found = True
            target_rank = rank
            match_type = "exact"
            break
        # Check for domain match (smart matching)
        elif _domains_match(target_domain, item_domain):
            target_found = True
            target_rank = rank
            match_type = "domain"
            break
        else:
            competitors_above.append(item_domain)

    return {
        "target_found": target_found,
        "target_rank": target_rank,
        "match_type": match_type,
        "competitors_above": competitors_above,
    }


# ─── Graph Definition ─────────────────────────────────────────────────────────

def create_visibility_graph() -> StateGraph:
    """Build the AI visibility checker graph."""
    graph = StateGraph(VisibilityState)

    graph.add_node("query_llm", query_llm_node)
    graph.add_node("validate_urls", validate_urls_node)
    graph.add_node("rank_checker", rank_checker_node)

    graph.set_entry_point("query_llm")

    # Conditional: if LLM failed, skip to end
    def should_validate(state: VisibilityState) -> str:
        if state.get("llm_error") or not state.get("raw_results"):
            return "rank_checker"
        return "validate_urls"

    graph.add_conditional_edges(
        "query_llm",
        should_validate,
        {
            "validate_urls": "validate_urls",
            "rank_checker": "rank_checker",
        },
    )

    graph.add_edge("validate_urls", "rank_checker")
    graph.add_edge("rank_checker", END)

    return graph


# ─── Public API ───────────────────────────────────────────────────────────────

_compiled_visibility_graph = None


def _get_compiled_visibility_graph():
    """Lazy-compile the visibility graph."""
    global _compiled_visibility_graph
    if _compiled_visibility_graph is None:
        graph = create_visibility_graph()
        _compiled_visibility_graph = graph.compile()
    return _compiled_visibility_graph


async def run_visibility_check(
    query: str,
    target_url: str,
    provider: str = "groq",
    num_results: int = 30,
) -> dict:
    """
    Execute the AI visibility checker workflow.

    Args:
        query: Search query to simulate
        target_url: URL to look for in results
        provider: "groq" or "anthropic"
        num_results: How many results to request (max 30)

    Returns:
        Complete visibility check results
    """
    compiled = _get_compiled_visibility_graph()

    # Validate provider
    if provider not in ("groq", "anthropic"):
        provider = "groq"

    # Cap results at 30
    num_results = min(max(num_results, 5), 30)

    initial_state: VisibilityState = {
        "query": query,
        "target_url": target_url,
        "provider": provider,
        "num_results": num_results,
        "raw_results": [],
        "llm_error": None,
        "validated_results": [],
        "target_found": False,
        "target_rank": None,
        "match_type": "not_found",
        "competitors_above": [],
        "total_valid_results": 0,
        "token_usage": None,
        "model_used": "",
    }

    final_state = await compiled.ainvoke(initial_state)

    return {
        "query": final_state.get("query", query),
        "target_url": final_state.get("target_url", target_url),
        "provider": final_state.get("provider", provider),
        "model": final_state.get("model_used", ""),
        "results": final_state.get("validated_results", []),
        "target_found": final_state.get("target_found", False),
        "target_rank": final_state.get("target_rank"),
        "match_type": final_state.get("match_type", "not_found"),
        "total_valid_results": final_state.get("total_valid_results", 0),
        "competitors_above": final_state.get("competitors_above", []),
        "token_usage": final_state.get("token_usage"),
        "error": final_state.get("llm_error"),
    }

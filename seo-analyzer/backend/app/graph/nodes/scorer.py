"""
Scorer Node - Aggregates all analysis results into a final health score.

This is the LAST node in the graph. It:
1. Reads scores from all analyzer nodes
2. Applies weights (matching the claude-seo methodology)
3. Detects site type from content signals
4. Prioritizes recommendations
5. Returns the final unified result
"""
from __future__ import annotations


import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState

# Scoring weights (must sum to 1.0)
# Matches claude-seo's methodology
WEIGHTS = {
    "technical": 0.22,
    "content": 0.23,
    "onpage": 0.20,
    "schema": 0.10,
    "performance": 0.15,
    "security": 0.10,
}


def _detect_site_type(html: str, url: str) -> str:
    """
    Auto-detect the type of website from page signals.
    This affects which recommendations are most relevant.
    """
    text = html.lower() if html else ""
    url_lower = url.lower()

    # E-commerce signals
    ecommerce_signals = [
        "add to cart", "buy now", "shopping cart", "/cart", "/checkout",
        "/products", "/collections", "product-price", "shopify",
    ]
    if sum(1 for s in ecommerce_signals if s in text or s in url_lower) >= 2:
        return "ecommerce"

    # SaaS signals
    saas_signals = [
        "pricing", "free trial", "sign up", "/features", "/integrations",
        "/docs", "/api", "get started", "demo",
    ]
    if sum(1 for s in saas_signals if s in text or s in url_lower) >= 2:
        return "saas"

    # Local business signals
    local_signals = [
        "serving", "our location", "visit us", "directions",
        "phone:", "tel:", "google maps", "local",
    ]
    if sum(1 for s in local_signals if s in text or s in url_lower) >= 2:
        return "local"

    # Publisher/blog signals
    publisher_signals = [
        "/blog", "/articles", "/news", "published", "author",
        "article", "read more", "subscribe", "newsletter",
    ]
    if sum(1 for s in publisher_signals if s in text or s in url_lower) >= 2:
        return "publisher"

    # Agency signals
    agency_signals = [
        "/case-studies", "/portfolio", "/work", "/clients",
        "our work", "industries we serve",
    ]
    if sum(1 for s in agency_signals if s in text or s in url_lower) >= 2:
        return "agency"

    return "other"


def _prioritize_issues(all_issues: list[dict]) -> list[dict]:
    """Sort issues by severity and deduplicate."""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    seen_titles = set()
    unique_issues = []

    for issue in all_issues:
        title = issue.get("title", "")
        if title not in seen_titles:
            seen_titles.add(title)
            unique_issues.append(issue)

    return sorted(unique_issues, key=lambda x: severity_order.get(x.get("severity", "low"), 4))


def _generate_recommendations(issues: list[dict], site_type: str) -> list[dict]:
    """Generate prioritized action plan from issues."""
    recommendations = []
    priority = 1

    for issue in issues:
        if issue.get("severity") in ("critical", "high"):
            recommendations.append({
                "priority": priority,
                "action": issue.get("recommendation", ""),
                "impact": issue.get("impact", ""),
                "category": issue.get("category", ""),
                "severity": issue.get("severity", ""),
                "effort": "medium",  # Could be enhanced with more context
            })
            priority += 1

    # Add site-type-specific recommendations
    type_recs = {
        "ecommerce": "Ensure Product schema with offers, reviews, and availability for rich results.",
        "saas": "Add SoftwareApplication schema and FAQ/HowTo for feature pages.",
        "local": "Verify Google Business Profile, add LocalBusiness schema with opening hours.",
        "publisher": "Use Article schema with author, datePublished, and proper breadcrumbs.",
    }
    if site_type in type_recs:
        recommendations.append({
            "priority": priority,
            "action": type_recs[site_type],
            "impact": "Industry-specific optimization for your site type.",
            "category": "strategy",
            "severity": "medium",
            "effort": "medium",
        })

    return recommendations[:20]  # Cap at 20 recommendations


async def scorer_node(state: SEOState) -> dict:
    """
    Final node: compute weighted health score and compile the audit report.
    """
    html = state.get("html", "")
    url = state.get("url", "")

    # Extract scores from each analyzer
    technical = state.get("technical_result", {}) or {}
    content = state.get("content_result", {}) or {}
    onpage = state.get("onpage_result", {}) or {}
    schema = state.get("schema_result", {}) or {}
    performance = state.get("performance_result", {}) or {}
    security = state.get("security_result", {}) or {}

    scores = {
        "technical": technical.get("score", 0),
        "content": content.get("score", 0),
        "onpage": onpage.get("score", 0),
        "schema": schema.get("score", 0),
        "performance": performance.get("score", 0),
        "security": security.get("score", 0),
    }

    # Weighted health score
    health_score = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    health_score = round(health_score, 1)

    # Detect site type
    site_type = _detect_site_type(html, url)

    # Aggregate all issues
    all_issues = []
    for result in [technical, content, onpage, schema, performance, security]:
        all_issues.extend(result.get("issues", []))

    # Prioritize and deduplicate
    prioritized_issues = _prioritize_issues(all_issues)

    # Count by severity
    critical_count = sum(1 for i in prioritized_issues if i.get("severity") == "critical")
    high_count = sum(1 for i in prioritized_issues if i.get("severity") == "high")
    medium_count = sum(1 for i in prioritized_issues if i.get("severity") == "medium")
    low_count = sum(1 for i in prioritized_issues if i.get("severity") == "low")

    # Generate recommendations
    recommendations = _generate_recommendations(prioritized_issues, site_type)

    return {
        "health_score": health_score,
        "site_type": site_type,
        "issues": prioritized_issues,
        "recommendations": recommendations,
    }

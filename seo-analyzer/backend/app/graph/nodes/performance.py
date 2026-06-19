"""
Performance Analyzer Node (Core Web Vitals).

Uses Google PageSpeed Insights API to get real performance data:
- LCP (Largest Contentful Paint) — loading speed
- INP (Interaction to Next Paint) — interactivity (replaced FID in March 2024)
- CLS (Cumulative Layout Shift) — visual stability
- FCP (First Contentful Paint) — perceived speed
- TTFB (Time to First Byte) — server response time

If no API key is configured, falls back to HTML-based heuristic analysis.
"""
from __future__ import annotations


from typing import Optional

import httpx

from app.config import settings
from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity

# Core Web Vitals thresholds (2024+)
CWV_THRESHOLDS = {
    "LCP": {"good": 2500, "needs_improvement": 4000, "unit": "ms"},
    "INP": {"good": 200, "needs_improvement": 500, "unit": "ms"},
    "CLS": {"good": 0.1, "needs_improvement": 0.25, "unit": "score"},
    "FCP": {"good": 1800, "needs_improvement": 3000, "unit": "ms"},
    "TTFB": {"good": 800, "needs_improvement": 1800, "unit": "ms"},
}


def _rate_metric(value: float, metric_name: str) -> str:
    """Rate a metric as good/needs-improvement/poor."""
    thresholds = CWV_THRESHOLDS.get(metric_name, {})
    if not thresholds:
        return "unknown"
    if value <= thresholds["good"]:
        return "good"
    elif value <= thresholds["needs_improvement"]:
        return "needs_improvement"
    return "poor"


async def _fetch_pagespeed_data(url: str) -> Optional[dict]:
    """
    Call Google PageSpeed Insights API.
    Returns None if no API key configured.
    
    The PSI API is free (25,000 requests/day) and returns both
    lab data (Lighthouse) and field data (CrUX — real user metrics).
    """
    if not settings.PAGESPEED_API_KEY:
        return None

    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "strategy": "mobile",  # Mobile-first (matches Google's indexing)
        "category": "performance",
    }
    headers = {
        "X-Goog-Api-Key": settings.PAGESPEED_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(api_url, params=params, headers=headers)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    return None


def _parse_psi_response(data: dict) -> dict:
    """Parse PageSpeed Insights API response into our format."""
    result = {
        "source": "pagespeed_insights",
        "strategy": "mobile",
        "performance_score": 0,
        "metrics": {},
    }

    # Lighthouse performance score (0-100)
    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    perf = categories.get("performance", {})
    result["performance_score"] = int((perf.get("score", 0) or 0) * 100)

    # Lab metrics from Lighthouse
    audits = lighthouse.get("audits", {})

    # LCP
    lcp_audit = audits.get("largest-contentful-paint", {})
    if lcp_audit:
        lcp_ms = lcp_audit.get("numericValue", 0)
        result["metrics"]["LCP"] = {
            "value": lcp_ms,
            "display": lcp_audit.get("displayValue", ""),
            "rating": _rate_metric(lcp_ms, "LCP"),
            "unit": "ms",
        }

    # CLS
    cls_audit = audits.get("cumulative-layout-shift", {})
    if cls_audit:
        cls_val = cls_audit.get("numericValue", 0)
        result["metrics"]["CLS"] = {
            "value": cls_val,
            "display": cls_audit.get("displayValue", ""),
            "rating": _rate_metric(cls_val, "CLS"),
            "unit": "score",
        }

    # FCP
    fcp_audit = audits.get("first-contentful-paint", {})
    if fcp_audit:
        fcp_ms = fcp_audit.get("numericValue", 0)
        result["metrics"]["FCP"] = {
            "value": fcp_ms,
            "display": fcp_audit.get("displayValue", ""),
            "rating": _rate_metric(fcp_ms, "FCP"),
            "unit": "ms",
        }

    # TTFB (server response time)
    ttfb_audit = audits.get("server-response-time", {})
    if ttfb_audit:
        ttfb_ms = ttfb_audit.get("numericValue", 0)
        result["metrics"]["TTFB"] = {
            "value": ttfb_ms,
            "display": ttfb_audit.get("displayValue", ""),
            "rating": _rate_metric(ttfb_ms, "TTFB"),
            "unit": "ms",
        }

    # Field data (CrUX — real user metrics, if available)
    crux = data.get("loadingExperience", {})
    crux_metrics = crux.get("metrics", {})

    if "INTERACTION_TO_NEXT_PAINT" in crux_metrics:
        inp_data = crux_metrics["INTERACTION_TO_NEXT_PAINT"]
        inp_p75 = inp_data.get("percentile", 0)
        result["metrics"]["INP"] = {
            "value": inp_p75,
            "display": f"{inp_p75} ms",
            "rating": _rate_metric(inp_p75, "INP"),
            "unit": "ms",
            "source": "field_data",
        }

    if "LARGEST_CONTENTFUL_PAINT_MS" in crux_metrics:
        lcp_field = crux_metrics["LARGEST_CONTENTFUL_PAINT_MS"]
        lcp_p75 = lcp_field.get("percentile", 0)
        # Field data overrides lab data (more accurate)
        result["metrics"]["LCP"] = {
            "value": lcp_p75,
            "display": f"{lcp_p75} ms",
            "rating": _rate_metric(lcp_p75, "LCP"),
            "unit": "ms",
            "source": "field_data",
        }

    return result


def _heuristic_performance(html: str, headers: dict) -> dict:
    """
    Fallback: estimate performance from HTML source when no API key is available.
    This is approximate but still useful.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")

    result = {
        "source": "heuristic",
        "strategy": "estimated",
        "performance_score": 70,  # Default assumption
        "metrics": {},
        "warnings": ["No PageSpeed API key — using HTML-based heuristics"],
    }

    issues_found = 0

    # Check page size
    page_size_kb = len(html.encode("utf-8")) / 1024
    if page_size_kb > 500:
        issues_found += 2
    elif page_size_kb > 200:
        issues_found += 1

    # Count render-blocking resources
    blocking_css = soup.find_all("link", {"rel": "stylesheet"})
    blocking_js = [s for s in soup.find_all("script", src=True) if not s.get("async") and not s.get("defer")]

    if len(blocking_css) > 5:
        issues_found += 1
    if len(blocking_js) > 3:
        issues_found += 2

    # Check for large images without lazy loading
    images = soup.find_all("img")
    non_lazy = [img for img in images if not img.get("loading") == "lazy"]
    if len(non_lazy) > 5:
        issues_found += 1

    # Check for preload hints
    preloads = soup.find_all("link", {"rel": "preload"})

    # Estimate score
    result["performance_score"] = max(20, 85 - (issues_found * 10))
    result["metrics"]["page_size"] = {
        "value": round(page_size_kb, 1),
        "unit": "KB",
        "rating": "good" if page_size_kb < 200 else ("needs_improvement" if page_size_kb < 500 else "poor"),
    }
    result["metrics"]["blocking_resources"] = {
        "css": len(blocking_css),
        "js_sync": len(blocking_js),
        "rating": "good" if len(blocking_js) <= 2 else "needs_improvement",
    }
    result["metrics"]["images_without_lazy_load"] = {
        "value": len(non_lazy),
        "total_images": len(images),
        "rating": "good" if len(non_lazy) <= 3 else "needs_improvement",
    }

    return result


async def performance_analyzer_node(state: SEOState) -> dict:
    """
    Analyze page performance and Core Web Vitals.
    Uses PageSpeed Insights API if available, falls back to heuristics.
    """
    url = state.get("url", "")
    html = state.get("html", "")
    headers = state.get("headers", {})

    issues: list[dict] = []
    score = 100

    # Try PageSpeed Insights API first
    psi_data = await _fetch_pagespeed_data(url)

    if psi_data:
        perf_data = _parse_psi_response(psi_data)
    else:
        perf_data = _heuristic_performance(html, headers)

    # Evaluate metrics and create issues
    metrics = perf_data.get("metrics", {})

    # LCP
    lcp = metrics.get("LCP", {})
    if lcp and lcp.get("rating") == "poor":
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="performance",
            title=f"Poor LCP: {lcp.get('display', 'N/A')}",
            description=f"Largest Contentful Paint is {lcp.get('value', 0)}ms (threshold: <2500ms).",
            recommendation="Optimize LCP: preload hero image, reduce server response time, eliminate render-blocking resources.",
            impact="LCP is a Core Web Vital and direct ranking factor. Poor LCP = lower rankings.",
        ).model_dump())
        score -= 25
    elif lcp and lcp.get("rating") == "needs_improvement":
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="performance",
            title=f"LCP needs improvement: {lcp.get('display', 'N/A')}",
            description=f"LCP is {lcp.get('value', 0)}ms (goal: <2500ms).",
            recommendation="Preload key resources, optimize images, reduce TTFB.",
            impact="LCP between 2.5-4s puts you in the 'needs improvement' bucket.",
        ).model_dump())
        score -= 10

    # INP
    inp = metrics.get("INP", {})
    if inp and inp.get("rating") == "poor":
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="performance",
            title=f"Poor INP: {inp.get('display', 'N/A')}",
            description=f"Interaction to Next Paint is {inp.get('value', 0)}ms (threshold: <200ms).",
            recommendation="Break up long tasks, reduce JavaScript execution time, defer non-critical scripts.",
            impact="INP replaced FID as the interactivity Core Web Vital. Poor INP = ranking penalty.",
        ).model_dump())
        score -= 25
    elif inp and inp.get("rating") == "needs_improvement":
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="performance",
            title=f"INP needs improvement: {inp.get('display', 'N/A')}",
            description=f"INP is {inp.get('value', 0)}ms (goal: <200ms).",
            recommendation="Optimize event handlers, use web workers for heavy computation.",
            impact="INP 200-500ms puts you in the 'needs improvement' range.",
        ).model_dump())
        score -= 10

    # CLS
    cls = metrics.get("CLS", {})
    if cls and cls.get("rating") == "poor":
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="performance",
            title=f"Poor CLS: {cls.get('display', 'N/A')}",
            description=f"Cumulative Layout Shift is {cls.get('value', 0)} (threshold: <0.1).",
            recommendation="Set explicit dimensions on images/ads, avoid inserting content above existing content.",
            impact="CLS measures visual stability — shifts frustrate users and hurt rankings.",
        ).model_dump())
        score -= 15

    # Overall performance score from PSI
    psi_score = perf_data.get("performance_score", 0)
    if psi_score < 50:
        score = min(score, 40)
    elif psi_score < 70:
        score = min(score, 60)

    score = max(0, min(100, score))

    return {
        "performance_result": {
            "score": score,
            "lcp": lcp,
            "inp": inp,
            "cls": cls,
            "fcp": metrics.get("FCP", {}),
            "ttfb": metrics.get("TTFB", {}),
            "page_size": metrics.get("page_size", {}),
            "psi_score": psi_score,
            "source": perf_data.get("source", "unknown"),
            "issues": issues,
        }
    }

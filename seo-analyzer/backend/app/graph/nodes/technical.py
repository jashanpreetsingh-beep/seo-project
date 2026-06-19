"""
Technical SEO Analyzer Node.

Checks:
- robots.txt accessibility and rules
- XML sitemap presence and validity
- Canonical tag correctness
- Redirect chains (too many hops = bad)
- HTTPS enforcement
- Mobile-friendliness signals (viewport meta)
- Crawlability signals
"""
from __future__ import annotations


from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity


async def _check_robots_txt(url: str) -> dict:
    """Fetch and analyze robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = {
        "url": robots_url,
        "exists": False,
        "allows_crawling": True,
        "has_sitemap": False,
        "sitemap_urls": [],
        "disallow_rules": [],
        "content": "",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                result["exists"] = True
                result["content"] = resp.text[:5000]  # Cap at 5KB

                for line in resp.text.splitlines():
                    line = line.strip().lower()
                    if line.startswith("disallow:"):
                        rule = line.split(":", 1)[1].strip()
                        result["disallow_rules"].append(rule)
                        if rule == "/":
                            result["allows_crawling"] = False
                    elif line.startswith("sitemap:"):
                        sitemap_url = line.split(":", 1)[1].strip()
                        # Reconstruct with proper case from original
                        for orig_line in resp.text.splitlines():
                            if orig_line.strip().lower() == line:
                                sitemap_url = orig_line.strip().split(":", 1)[1].strip()
                                break
                        result["sitemap_urls"].append(sitemap_url)
                        result["has_sitemap"] = True
    except Exception:
        pass

    return result


async def _check_sitemap(url: str, robots_sitemaps: list[str]) -> dict:
    """Check XML sitemap availability."""
    parsed = urlparse(url)
    result = {
        "found": False,
        "url": "",
        "url_count": 0,
        "is_index": False,
        "errors": [],
    }

    # Try sitemaps from robots.txt first, then common paths
    sitemap_candidates = robots_sitemaps + [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
    ]

    for sitemap_url in sitemap_candidates:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(sitemap_url)
                if resp.status_code == 200 and "xml" in resp.headers.get("content-type", "").lower():
                    result["found"] = True
                    result["url"] = sitemap_url

                    # Count URLs in sitemap
                    soup = BeautifulSoup(resp.text, "lxml-xml")
                    urls = soup.find_all("url")
                    sitemaps = soup.find_all("sitemap")

                    if sitemaps:
                        result["is_index"] = True
                        result["url_count"] = len(sitemaps)
                    else:
                        result["url_count"] = len(urls)
                    break
        except Exception:
            continue

    return result


def _check_canonicals(html: str, url: str) -> dict:
    """Check canonical tag presence and correctness."""
    soup = BeautifulSoup(html, "lxml")
    result = {
        "has_canonical": False,
        "canonical_url": "",
        "is_self_referencing": False,
        "issues": [],
    }

    canonical = soup.find("link", {"rel": "canonical"})
    if canonical and canonical.get("href"):
        result["has_canonical"] = True
        result["canonical_url"] = canonical["href"]
        result["is_self_referencing"] = canonical["href"].rstrip("/") == url.rstrip("/")
    else:
        result["issues"].append("No canonical tag found")

    return result


def _check_mobile(html: str) -> dict:
    """Check mobile-friendliness signals from HTML."""
    soup = BeautifulSoup(html, "lxml")
    result = {
        "has_viewport": False,
        "viewport_content": "",
        "issues": [],
    }

    viewport = soup.find("meta", {"name": "viewport"})
    if viewport and viewport.get("content"):
        result["has_viewport"] = True
        result["viewport_content"] = viewport["content"]
        if "width=device-width" not in viewport["content"]:
            result["issues"].append("Viewport does not use width=device-width")
    else:
        result["issues"].append("No viewport meta tag — not mobile-friendly")

    return result


async def technical_analyzer_node(state: SEOState) -> dict:
    """
    Run technical SEO analysis.
    
    This node checks infrastructure-level SEO signals that affect
    whether search engines can discover, crawl, and index the page.
    """
    url = state["url"]
    html = state.get("html", "")
    headers = state.get("headers", {})
    redirect_chain = state.get("redirect_chain", [])

    issues: list[dict] = []
    score = 100  # Start perfect, deduct for issues

    # 1. Robots.txt
    robots = await _check_robots_txt(url)
    if not robots["exists"]:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="technical",
            title="No robots.txt found",
            description="The site has no robots.txt file at the root.",
            recommendation="Create a robots.txt file to guide search engine crawlers.",
            impact="Crawlers have no directives — they'll crawl everything, which may waste budget.",
        ).model_dump())
        score -= 5
    elif not robots["allows_crawling"]:
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="technical",
            title="robots.txt blocks all crawling",
            description="Disallow: / is set for all user agents.",
            recommendation="Remove the blanket Disallow: / rule unless the site is intentionally hidden.",
            impact="Search engines cannot index any page on this site.",
        ).model_dump())
        score -= 40

    # 2. Sitemap
    sitemap = await _check_sitemap(url, robots.get("sitemap_urls", []))
    if not sitemap["found"]:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="technical",
            title="No XML sitemap found",
            description="No accessible XML sitemap at common paths or referenced in robots.txt.",
            recommendation="Create and submit an XML sitemap to help search engines discover all pages.",
            impact="Search engines may miss pages, especially deep or orphaned ones.",
        ).model_dump())
        score -= 10

    # 3. Canonicals
    canonicals = _check_canonicals(html, url)
    if not canonicals["has_canonical"]:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="technical",
            title="Missing canonical tag",
            description="No rel=canonical link found in the page head.",
            recommendation="Add a self-referencing canonical tag to prevent duplicate content issues.",
            impact="Duplicate content may dilute ranking signals across multiple URLs.",
        ).model_dump())
        score -= 10

    # 4. Redirect chain
    if len(redirect_chain) > 2:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="technical",
            title=f"Long redirect chain ({len(redirect_chain)} hops)",
            description=f"The URL goes through {len(redirect_chain)} redirects before reaching the final page.",
            recommendation="Reduce the redirect chain to at most 1 hop (direct to final URL).",
            impact="Each redirect adds latency and can lose link equity (PageRank dampening).",
        ).model_dump())
        score -= 5 * min(len(redirect_chain) - 1, 4)

    # 5. HTTPS
    if not url.startswith("https://"):
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="technical",
            title="Site not using HTTPS",
            description="The page is served over HTTP without TLS encryption.",
            recommendation="Install an SSL certificate and redirect all HTTP to HTTPS.",
            impact="Google uses HTTPS as a ranking signal. Browsers show 'Not Secure' warnings.",
        ).model_dump())
        score -= 20

    # 6. Mobile
    mobile = _check_mobile(html)
    if not mobile["has_viewport"]:
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="technical",
            title="Not mobile-friendly (no viewport)",
            description="Missing viewport meta tag — page won't render correctly on mobile.",
            recommendation="Add <meta name='viewport' content='width=device-width, initial-scale=1'>",
            impact="Google uses mobile-first indexing. No viewport = poor mobile experience = lower rankings.",
        ).model_dump())
        score -= 20

    # Clamp score
    score = max(0, min(100, score))

    return {
        "technical_result": {
            "score": score,
            "robots_txt": robots,
            "sitemap": sitemap,
            "canonicals": canonicals,
            "redirects": {"chain": redirect_chain, "hop_count": len(redirect_chain)},
            "https": {"is_https": url.startswith("https://")},
            "mobile_friendly": mobile,
            "issues": issues,
        }
    }

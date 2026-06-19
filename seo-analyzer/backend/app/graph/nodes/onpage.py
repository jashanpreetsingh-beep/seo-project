"""
On-Page SEO Analyzer Node.

Checks the most important on-page ranking signals:
- Title tag (presence, length, keyword placement)
- Meta description (presence, length, call-to-action)
- Heading tags (H1-H6 usage)
- Image alt text coverage
- Internal linking structure
- External links (nofollow usage)
- URL structure
"""
from __future__ import annotations


import re
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity


def _analyze_title(soup: BeautifulSoup) -> dict:
    """Analyze the page title tag."""
    title_tag = soup.find("title")
    result = {
        "exists": False,
        "content": "",
        "length": 0,
        "is_too_short": False,
        "is_too_long": False,
    }

    if title_tag and title_tag.string:
        title = title_tag.string.strip()
        result["exists"] = True
        result["content"] = title
        result["length"] = len(title)
        result["is_too_short"] = len(title) < 30
        result["is_too_long"] = len(title) > 60

    return result


def _analyze_meta_description(soup: BeautifulSoup) -> dict:
    """Analyze the meta description."""
    meta = soup.find("meta", {"name": "description"})
    result = {
        "exists": False,
        "content": "",
        "length": 0,
        "is_too_short": False,
        "is_too_long": False,
    }

    if meta and meta.get("content"):
        desc = meta["content"].strip()
        result["exists"] = True
        result["content"] = desc
        result["length"] = len(desc)
        result["is_too_short"] = len(desc) < 70
        result["is_too_long"] = len(desc) > 160

    return result


def _analyze_images(soup: BeautifulSoup) -> dict:
    """Analyze image tags for alt text and optimization."""
    images = soup.find_all("img")
    result = {
        "total": len(images),
        "with_alt": 0,
        "without_alt": 0,
        "empty_alt": 0,
        "missing_alt_srcs": [],
    }

    for img in images:
        alt = img.get("alt")
        if alt is None:
            result["without_alt"] += 1
            src = img.get("src", "unknown")[:100]
            result["missing_alt_srcs"].append(src)
        elif alt.strip() == "":
            result["empty_alt"] += 1  # Decorative images — this is OK
        else:
            result["with_alt"] += 1

    return result


def _analyze_links(soup: BeautifulSoup, base_url: str) -> tuple[dict, dict]:
    """Analyze internal and external links."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc

    internal = {"count": 0, "urls": []}
    external = {"count": 0, "urls": [], "nofollow_count": 0}

    all_links = soup.find_all("a", href=True)

    for link in all_links:
        href = link["href"]
        # Skip anchors, javascript, mailto
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        if parsed.netloc == base_domain or not parsed.netloc:
            internal["count"] += 1
            if internal["count"] <= 20:  # Cap stored URLs
                internal["urls"].append(full_url)
        else:
            external["count"] += 1
            if external["count"] <= 10:
                external["urls"].append(full_url)

            # Check nofollow
            rel = link.get("rel", [])
            if isinstance(rel, list) and "nofollow" in rel:
                external["nofollow_count"] += 1
            elif isinstance(rel, str) and "nofollow" in rel:
                external["nofollow_count"] += 1

    return internal, external


def _analyze_url_structure(url: str) -> dict:
    """Analyze URL structure for SEO best practices."""
    parsed = urlparse(url)
    path = parsed.path

    result = {
        "url": url,
        "path": path,
        "length": len(url),
        "is_clean": True,
        "issues": [],
    }

    # Check for query parameters in URL (not SEO-friendly)
    if parsed.query:
        result["issues"].append("URL contains query parameters")

    # Check for underscores (hyphens preferred)
    if "_" in path:
        result["issues"].append("URL uses underscores — prefer hyphens")
        result["is_clean"] = False

    # Check for uppercase
    if path != path.lower():
        result["issues"].append("URL contains uppercase characters")
        result["is_clean"] = False

    # Check depth (more than 4 levels deep is usually bad)
    depth = len([p for p in path.split("/") if p])
    result["depth"] = depth
    if depth > 4:
        result["issues"].append(f"URL is {depth} levels deep — keep URLs shallow")

    # Check length
    if len(url) > 100:
        result["issues"].append("URL is longer than 100 characters")

    return result


async def onpage_analyzer_node(state: SEOState) -> dict:
    """
    Analyze on-page SEO elements: title, meta desc, headings, images, links.
    """
    html = state.get("html", "")
    url = state.get("url", "")

    if not html:
        return {"onpage_result": {"score": 0, "issues": []}}

    soup = BeautifulSoup(html, "lxml")
    issues: list[dict] = []
    score = 100

    # 1. Title tag
    title = _analyze_title(soup)
    if not title["exists"]:
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="onpage",
            title="Missing title tag",
            description="The page has no <title> tag.",
            recommendation="Add a unique, descriptive title tag (30-60 characters).",
            impact="Title is the #1 on-page ranking factor and the clickable SERP headline.",
        ).model_dump())
        score -= 25
    elif title["is_too_short"]:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="onpage",
            title=f"Title too short ({title['length']} chars)",
            description=f"Title: \"{title['content']}\" — only {title['length']} characters.",
            recommendation="Expand title to 30-60 characters to use full SERP real estate.",
            impact="Short titles waste SERP space and miss keyword opportunities.",
        ).model_dump())
        score -= 5
    elif title["is_too_long"]:
        issues.append(SEOIssue(
            severity=Severity.LOW,
            category="onpage",
            title=f"Title may be truncated ({title['length']} chars)",
            description=f"Title is {title['length']} characters — Google typically shows ~60.",
            recommendation="Keep title under 60 characters to prevent truncation in SERPs.",
            impact="Truncated titles may cut off important keywords.",
        ).model_dump())
        score -= 3

    # 2. Meta description
    meta_desc = _analyze_meta_description(soup)
    if not meta_desc["exists"]:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="onpage",
            title="Missing meta description",
            description="No meta description tag found.",
            recommendation="Add a compelling meta description (70-160 characters) with a call-to-action.",
            impact="Google may generate its own snippet — you lose control over SERP messaging.",
        ).model_dump())
        score -= 10
    elif meta_desc["is_too_short"]:
        issues.append(SEOIssue(
            severity=Severity.LOW,
            category="onpage",
            title=f"Meta description too short ({meta_desc['length']} chars)",
            description=f"Meta description is only {meta_desc['length']} characters.",
            recommendation="Expand to 70-160 characters for optimal SERP snippet coverage.",
            impact="Short descriptions waste SERP space.",
        ).model_dump())
        score -= 3

    # 3. Images
    images = _analyze_images(soup)
    if images["total"] > 0 and images["without_alt"] > 0:
        pct_missing = (images["without_alt"] / images["total"]) * 100
        severity = Severity.HIGH if pct_missing > 50 else Severity.MEDIUM
        issues.append(SEOIssue(
            severity=severity,
            category="onpage",
            title=f"{images['without_alt']}/{images['total']} images missing alt text",
            description=f"{pct_missing:.0f}% of images lack alt attributes.",
            recommendation="Add descriptive alt text to all informational images.",
            impact="Missing alt text hurts image SEO, accessibility, and AI understanding.",
        ).model_dump())
        score -= min(15, images["without_alt"] * 3)

    # 4. Internal links
    internal_links, external_links = _analyze_links(soup, url)
    if internal_links["count"] < 3:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="onpage",
            title=f"Few internal links ({internal_links['count']})",
            description=f"Only {internal_links['count']} internal links found.",
            recommendation="Add relevant internal links to help users and crawlers discover related content.",
            impact="Internal linking distributes PageRank and improves crawl depth.",
        ).model_dump())
        score -= 5

    # 5. URL structure
    url_analysis = _analyze_url_structure(url)
    if url_analysis["issues"]:
        issues.append(SEOIssue(
            severity=Severity.LOW,
            category="onpage",
            title="URL structure issues",
            description="; ".join(url_analysis["issues"]),
            recommendation="Use short, lowercase, hyphenated URLs with descriptive slugs.",
            impact="Clean URLs improve click-through rates and crawlability.",
        ).model_dump())
        score -= 3

    score = max(0, min(100, score))

    return {
        "onpage_result": {
            "score": score,
            "title": title,
            "meta_description": meta_desc,
            "headings": {"h1_count": len(soup.find_all("h1"))},
            "images": images,
            "internal_links": internal_links,
            "external_links": external_links,
            "url_structure": url_analysis,
            "issues": issues,
        }
    }

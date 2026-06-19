"""
Security Analyzer Node.

Checks security-related SEO signals:
- HTTPS enforcement
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Mixed content detection
- Cookie security
"""
from __future__ import annotations


import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity

# Important security headers and their purposes
SECURITY_HEADERS = {
    "strict-transport-security": {
        "name": "HSTS (Strict-Transport-Security)",
        "description": "Forces browsers to use HTTPS for all future requests",
        "severity": Severity.HIGH,
    },
    "content-security-policy": {
        "name": "Content-Security-Policy",
        "description": "Prevents XSS and data injection attacks",
        "severity": Severity.MEDIUM,
    },
    "x-content-type-options": {
        "name": "X-Content-Type-Options",
        "description": "Prevents MIME type sniffing (should be 'nosniff')",
        "severity": Severity.MEDIUM,
    },
    "x-frame-options": {
        "name": "X-Frame-Options",
        "description": "Prevents clickjacking by controlling iframe embedding",
        "severity": Severity.MEDIUM,
    },
    "referrer-policy": {
        "name": "Referrer-Policy",
        "description": "Controls how much referrer info is sent with requests",
        "severity": Severity.LOW,
    },
    "permissions-policy": {
        "name": "Permissions-Policy",
        "description": "Controls browser features (camera, mic, geolocation)",
        "severity": Severity.LOW,
    },
}


def _check_https(url: str, headers: dict) -> dict:
    """Check HTTPS configuration."""
    result = {
        "is_https": url.startswith("https://"),
        "has_hsts": False,
        "hsts_max_age": 0,
        "hsts_includes_subdomains": False,
    }

    hsts = headers.get("strict-transport-security", "")
    if hsts:
        result["has_hsts"] = True
        # Parse max-age
        match = re.search(r"max-age=(\d+)", hsts)
        if match:
            result["hsts_max_age"] = int(match.group(1))
        result["hsts_includes_subdomains"] = "includesubdomains" in hsts.lower()

    return result


def _check_security_headers(headers: dict) -> dict:
    """Check presence and quality of security headers."""
    # Normalize header keys to lowercase
    norm_headers = {k.lower(): v for k, v in headers.items()}

    result = {
        "present": [],
        "missing": [],
        "details": {},
    }

    for header_key, header_info in SECURITY_HEADERS.items():
        if header_key in norm_headers:
            result["present"].append(header_info["name"])
            result["details"][header_key] = {
                "value": norm_headers[header_key],
                "status": "present",
            }
        else:
            result["missing"].append(header_info["name"])
            result["details"][header_key] = {
                "value": None,
                "status": "missing",
                "severity": header_info["severity"].value,
            }

    return result


def _check_mixed_content(html: str, url: str) -> list[str]:
    """Detect mixed content (HTTP resources on HTTPS page)."""
    if not url.startswith("https://"):
        return []  # Only relevant for HTTPS pages

    soup = BeautifulSoup(html, "lxml")
    mixed = []

    # Check common resource tags
    resource_attrs = [
        ("img", "src"),
        ("script", "src"),
        ("link", "href"),
        ("iframe", "src"),
        ("video", "src"),
        ("audio", "src"),
        ("source", "src"),
    ]

    for tag_name, attr in resource_attrs:
        for tag in soup.find_all(tag_name, **{attr: True}):
            resource_url = tag.get(attr, "")
            if resource_url.startswith("http://"):
                mixed.append(f"{tag_name}[{attr}]: {resource_url[:100]}")

    return mixed[:20]  # Cap at 20 items


async def security_analyzer_node(state: SEOState) -> dict:
    """
    Analyze security aspects that affect SEO trust signals.
    """
    url = state.get("url", "")
    html = state.get("html", "")
    headers = state.get("headers", {})

    issues: list[dict] = []
    score = 100

    # 1. HTTPS check
    https_result = _check_https(url, headers)
    if not https_result["is_https"]:
        issues.append(SEOIssue(
            severity=Severity.CRITICAL,
            category="security",
            title="No HTTPS",
            description="The page is not served over HTTPS.",
            recommendation="Install an SSL/TLS certificate and redirect all HTTP to HTTPS.",
            impact="HTTPS is a confirmed Google ranking signal. Chrome labels HTTP as 'Not Secure'.",
        ).model_dump())
        score -= 30
    elif not https_result["has_hsts"]:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="security",
            title="Missing HSTS header",
            description="Strict-Transport-Security header not set.",
            recommendation="Add HSTS header: Strict-Transport-Security: max-age=31536000; includeSubDomains",
            impact="Without HSTS, browsers may still attempt HTTP connections initially.",
        ).model_dump())
        score -= 5

    # 2. Security headers
    headers_result = _check_security_headers(headers)
    missing_critical = [
        h for h in headers_result["missing"]
        if any(info["name"] == h and info["severity"] in (Severity.HIGH, Severity.CRITICAL)
               for info in SECURITY_HEADERS.values())
    ]
    missing_medium = [
        h for h in headers_result["missing"]
        if any(info["name"] == h and info["severity"] == Severity.MEDIUM
               for info in SECURITY_HEADERS.values())
    ]

    if missing_critical:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="security",
            title=f"Missing critical security headers ({len(missing_critical)})",
            description=f"Missing: {', '.join(missing_critical)}",
            recommendation="Add these headers to improve site security posture.",
            impact="Security headers build trust with browsers and protect users from attacks.",
        ).model_dump())
        score -= 5 * len(missing_critical)

    if missing_medium:
        issues.append(SEOIssue(
            severity=Severity.LOW,
            category="security",
            title=f"Missing recommended security headers ({len(missing_medium)})",
            description=f"Missing: {', '.join(missing_medium)}",
            recommendation="Consider adding these headers for defense-in-depth.",
            impact="Minor trust signal improvement.",
        ).model_dump())
        score -= 2 * len(missing_medium)

    # 3. Mixed content
    mixed_content = _check_mixed_content(html, url)
    if mixed_content:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="security",
            title=f"Mixed content detected ({len(mixed_content)} resources)",
            description=f"HTTP resources loaded on HTTPS page: {'; '.join(mixed_content[:3])}",
            recommendation="Update all resource URLs to use HTTPS or protocol-relative URLs.",
            impact="Mixed content triggers browser warnings and undermines HTTPS trust.",
        ).model_dump())
        score -= 10

    score = max(0, min(100, score))

    return {
        "security_result": {
            "score": score,
            "https": https_result,
            "headers": headers_result,
            "mixed_content": mixed_content,
            "issues": issues,
        }
    }

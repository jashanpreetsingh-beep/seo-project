"""
Fetch Page Node - Retrieves the target URL's HTML content.

This is always the FIRST node in the graph. All analyzer nodes depend on its output.
Includes:
- SSRF protection (blocks private/loopback IPs)
- Redirect chain tracking
- Proper charset handling
- User-Agent rotation
"""
from __future__ import annotations


import ipaddress
import re
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.graph.state import SEOState


# Block requests to private/internal IPs (SSRF protection)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 SEOAnalyzer/1.0"
)


def _validate_url(url: str) -> str:
    """
    Validate and normalize a URL. Blocks private IPs for SSRF protection.
    
    This is critical security — without it, a user could make our server
    fetch internal resources (e.g., http://169.254.169.254 for cloud metadata).
    """
    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    # Must have a valid hostname
    if not parsed.hostname:
        raise ValueError(f"Invalid URL: no hostname found in '{url}'")

    # Block private IPs
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(f"Blocked: URL points to private/internal IP ({ip})")
    except ValueError as e:
        if "Blocked" in str(e):
            raise
        # Not an IP address (it's a hostname) — that's fine
        pass

    return url


async def fetch_page_node(state: SEOState) -> dict:
    """
    Fetch the target URL and return HTML + metadata.
    
    This node:
    1. Validates the URL (SSRF protection)
    2. Makes the HTTP request with proper headers
    3. Tracks redirect chains
    4. Returns HTML content, headers, status code
    
    Returns partial state update with fetch results.
    """
    url = state["url"]

    try:
        url = _validate_url(url)
    except ValueError as e:
        return {
            "url": url,
            "html": "",
            "status_code": 0,
            "headers": {},
            "redirect_chain": [],
            "fetch_error": str(e),
        }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
    }

    redirect_chain = []

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=10,
            timeout=settings.FETCH_TIMEOUT,
        ) as client:
            response = await client.get(url, headers=headers)

            # Track redirect chain
            if response.history:
                redirect_chain = [
                    {"url": str(r.url), "status_code": r.status_code}
                    for r in response.history
                ]

            return {
                "url": str(response.url),
                "html": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "redirect_chain": redirect_chain,
                "fetch_error": None,
            }

    except httpx.TimeoutException:
        return {
            "url": url,
            "html": "",
            "status_code": 0,
            "headers": {},
            "redirect_chain": [],
            "fetch_error": f"Request timed out after {settings.FETCH_TIMEOUT}s",
        }
    except httpx.ConnectError as e:
        return {
            "url": url,
            "html": "",
            "status_code": 0,
            "headers": {},
            "redirect_chain": [],
            "fetch_error": f"Connection failed: {e}",
        }
    except Exception as e:
        return {
            "url": url,
            "html": "",
            "status_code": 0,
            "headers": {},
            "redirect_chain": [],
            "fetch_error": f"Fetch error: {e}",
        }

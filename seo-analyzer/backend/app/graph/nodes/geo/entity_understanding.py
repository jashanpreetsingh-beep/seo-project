"""
GEO Agent 1: Entity Understanding Score (25% of GEO Score).

Question: "Does AI understand who this business is?"

This agent evaluates whether an AI system could confidently identify:
- What the business does
- Who they serve
- Where they operate
- What makes them unique
- Who is behind the company

If a website says "Providing innovative solutions for businesses" — AI has no idea
what that means. This agent penalizes vague, generic entity descriptions.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.graph.state import SEOState


def _extract_entity_signals(soup: BeautifulSoup, text: str, url: str) -> dict:
    """Extract signals that help AI understand the business entity."""

    signals = {
        "business_name": {"found": False, "value": "", "score": 0},
        "industry": {"found": False, "value": "", "score": 0},
        "location": {"found": False, "value": "", "score": 0},
        "services_products": {"found": False, "items": [], "score": 0},
        "target_audience": {"found": False, "value": "", "score": 0},
        "unique_selling_proposition": {"found": False, "value": "", "score": 0},
        "people_behind": {"found": False, "items": [], "score": 0},
        "founding_year": {"found": False, "value": "", "score": 0},
    }

    text_lower = text.lower()

    # Business name detection
    # Check meta tags, OG tags, schema, title
    og_site = soup.find("meta", {"property": "og:site_name"})
    if og_site and og_site.get("content"):
        signals["business_name"]["found"] = True
        signals["business_name"]["value"] = og_site["content"]
        signals["business_name"]["score"] = 100

    if not signals["business_name"]["found"]:
        title = soup.find("title")
        if title and title.string:
            # Try to extract business name from title (usually before | or -)
            parts = re.split(r'[|\-–—]', title.string)
            if len(parts) > 1:
                name = parts[-1].strip() if len(parts[-1].strip()) < 40 else parts[0].strip()
                signals["business_name"]["found"] = True
                signals["business_name"]["value"] = name
                signals["business_name"]["score"] = 70

    # Industry detection
    industry_keywords = {
        "technology": ["software", "saas", "tech", "platform", "app", "digital"],
        "healthcare": ["health", "medical", "doctor", "clinic", "hospital", "dental", "therapy"],
        "finance": ["finance", "banking", "investment", "insurance", "fintech", "accounting"],
        "education": ["education", "learning", "course", "training", "university", "school"],
        "ecommerce": ["shop", "store", "buy", "product", "cart", "delivery", "ecommerce"],
        "marketing": ["marketing", "seo", "advertising", "agency", "branding", "content marketing"],
        "legal": ["law", "legal", "attorney", "lawyer", "litigation"],
        "real_estate": ["real estate", "property", "homes", "apartments", "rental"],
        "food_beverage": ["restaurant", "food", "catering", "menu", "delivery"],
        "consulting": ["consulting", "consultant", "advisory", "strategy"],
    }

    detected_industries = []
    for industry, keywords in industry_keywords.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches >= 2:
            detected_industries.append((industry, matches))

    if detected_industries:
        detected_industries.sort(key=lambda x: x[1], reverse=True)
        signals["industry"]["found"] = True
        signals["industry"]["value"] = detected_industries[0][0]
        signals["industry"]["score"] = min(100, detected_industries[0][1] * 25)

    # Location detection
    location_patterns = [
        r'\b(based in|located in|headquartered in|offices? in|serving)\s+([A-Z][a-zA-Z\s,]+)',
        r'\b(New York|San Francisco|London|Mumbai|Delhi|Bangalore|Singapore|Dubai|Toronto|Sydney|Berlin|Paris|Tokyo|Chicago|Los Angeles|Boston|Seattle|Austin)',
        r'\b\d{5}(-\d{4})?\b',  # ZIP codes
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            signals["location"]["found"] = True
            signals["location"]["value"] = match.group(0)[:50]
            signals["location"]["score"] = 80
            break

    # Address in schema or structured elements
    addr_elem = soup.find(attrs={"itemprop": "address"}) or soup.find(class_=re.compile(r"address", re.I))
    if addr_elem:
        signals["location"]["found"] = True
        signals["location"]["value"] = addr_elem.get_text(strip=True)[:80]
        signals["location"]["score"] = 100

    # Services/Products detection
    services_patterns = [
        r'(?:our|we offer|services include|we provide|specializ\w+ in)[:\s]+([\w\s,]+)',
        r'<li[^>]*>([\w\s]+(?:service|solution|product|consulting|development|design))',
    ]

    service_elements = soup.find_all(["li", "h2", "h3"], limit=50)
    service_keywords = ["service", "solution", "offering", "product", "package", "plan"]
    found_services = []

    for elem in service_elements:
        elem_text = elem.get_text(strip=True).lower()
        if any(kw in elem_text for kw in service_keywords) and len(elem_text) < 100:
            found_services.append(elem.get_text(strip=True))

    if found_services:
        signals["services_products"]["found"] = True
        signals["services_products"]["items"] = found_services[:10]
        signals["services_products"]["score"] = min(100, len(found_services) * 20)

    # Target audience detection
    audience_patterns = [
        r'(?:for|helping|designed for|built for|serving)\s+([\w\s]+(?:companies|businesses|startups|enterprises|teams|professionals|developers|marketers|creators))',
        r'(?:b2b|b2c|enterprise|small business|startup|freelancer|agency)',
    ]

    for pattern in audience_patterns:
        match = re.search(pattern, text_lower)
        if match:
            signals["target_audience"]["found"] = True
            signals["target_audience"]["value"] = match.group(0)[:60]
            signals["target_audience"]["score"] = 80
            break

    # USP detection (unique value propositions)
    usp_patterns = [
        r'(?:the only|unlike|what makes us|why choose|our difference|we\'re the|#1|number one|leading|first)',
        r'(?:unique|proprietary|patented|exclusive|award-winning|industry-leading)',
    ]

    for pattern in usp_patterns:
        if re.search(pattern, text_lower):
            signals["unique_selling_proposition"]["found"] = True
            signals["unique_selling_proposition"]["score"] = 60
            break

    # People behind the company
    people_patterns = [
        r'(?:founded by|co-?founder|ceo|cto|director|team lead|our team)',
        r'(?:Dr\.|PhD|MBA|certified|licensed|experienced)',
    ]

    for pattern in people_patterns:
        if re.search(pattern, text_lower):
            signals["people_behind"]["found"] = True
            signals["people_behind"]["score"] = 60
            break

    # Check for about page link or team section
    about_link = soup.find("a", href=re.compile(r"/about|/team|/our-team", re.I))
    if about_link:
        signals["people_behind"]["score"] = max(signals["people_behind"]["score"], 40)
        signals["people_behind"]["found"] = True

    # Founding year
    year_match = re.search(r'(?:since|founded|established|est\.?)\s*(\d{4})', text)
    if year_match:
        signals["founding_year"]["found"] = True
        signals["founding_year"]["value"] = year_match.group(1)
        signals["founding_year"]["score"] = 100

    return signals


def _check_vagueness(text: str) -> dict:
    """Detect vague, meaningless corporate language that confuses AI."""

    vague_phrases = [
        "innovative solutions",
        "cutting-edge technology",
        "world-class service",
        "premier provider",
        "one-stop shop",
        "synergy",
        "leveraging",
        "next-generation",
        "best-in-class",
        "seamless integration",
        "holistic approach",
        "paradigm shift",
        "disruptive",
        "turnkey solution",
        "end-to-end",
        "state of the art",
        "game changer",
        "think outside the box",
        "move the needle",
        "empower",
    ]

    text_lower = text.lower()
    found_vague = [p for p in vague_phrases if p in text_lower]

    # Check for generic descriptions
    generic_patterns = [
        r'we (?:help|provide|offer|deliver) (?:solutions|services|products) (?:to|for) (?:businesses|companies|clients)',
    ]
    generic_found = any(re.search(p, text_lower) for p in generic_patterns)

    return {
        "vague_phrases_found": found_vague,
        "vague_count": len(found_vague),
        "is_generic": generic_found,
        "penalty": min(30, len(found_vague) * 5 + (10 if generic_found else 0)),
    }


async def entity_understanding_node(state: SEOState) -> dict:
    """
    GEO Agent 1: Evaluate how well AI can understand the business entity.

    Scoring (25% of total GEO):
    - Business name identifiable: 15 pts
    - Industry clear: 15 pts
    - Location specified: 10 pts
    - Services/products explicit: 20 pts
    - Target audience defined: 15 pts
    - USP articulated: 10 pts
    - People/expertise visible: 10 pts
    - Founding/history: 5 pts
    - Penalty for vagueness: up to -30 pts
    """
    html = state.get("html", "")
    url = state.get("url", "")

    if not html:
        return {
            "geo_entity_result": {
                "score": 0,
                "signals": {},
                "issues": [],
                "vagueness": {},
            }
        }

    soup = BeautifulSoup(html, "lxml")

    # Extract visible text
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    # Analyze entity signals
    signals = _extract_entity_signals(BeautifulSoup(html, "lxml"), text, url)

    # Check vagueness
    vagueness = _check_vagueness(text)

    # Calculate score
    score = 0
    max_scores = {
        "business_name": 15,
        "industry": 15,
        "location": 10,
        "services_products": 20,
        "target_audience": 15,
        "unique_selling_proposition": 10,
        "people_behind": 10,
        "founding_year": 5,
    }

    for signal_key, max_score in max_scores.items():
        signal = signals.get(signal_key, {})
        if signal.get("found"):
            score += (signal.get("score", 0) / 100) * max_score

    # Apply vagueness penalty
    score = max(0, score - vagueness["penalty"])
    score = min(100, score)

    # Generate issues
    issues = []
    if not signals["business_name"]["found"]:
        issues.append({
            "signal": "business_name",
            "issue": "AI cannot identify business name clearly",
            "suggestion": "Add clear business name in title, OG tags, and schema markup",
            "impact": "+5 GEO points",
        })

    if not signals["industry"]["found"]:
        issues.append({
            "signal": "industry",
            "issue": "Industry/niche is unclear to AI",
            "suggestion": "State your industry explicitly: 'We are a [industry] company...'",
            "impact": "+5 GEO points",
        })

    if not signals["location"]["found"]:
        issues.append({
            "signal": "location",
            "issue": "No geographic signals for AI",
            "suggestion": "Add location information (city, state/country) in footer, about page, or schema",
            "impact": "+3 GEO points",
        })

    if not signals["services_products"]["found"]:
        issues.append({
            "signal": "services_products",
            "issue": "Services/products not explicitly listed",
            "suggestion": "Create clear service/product listings with descriptions AI can parse",
            "impact": "+7 GEO points",
        })

    if not signals["target_audience"]["found"]:
        issues.append({
            "signal": "target_audience",
            "issue": "Target audience undefined — AI doesn't know who you serve",
            "suggestion": "State clearly: 'We help [audience type] achieve [outcome]'",
            "impact": "+5 GEO points",
        })

    if vagueness["vague_count"] > 3:
        issues.append({
            "signal": "vagueness",
            "issue": f"Too many vague phrases ({vagueness['vague_count']}) — AI cannot extract meaning",
            "suggestion": "Replace corporate buzzwords with specific, factual statements about what you do",
            "impact": f"+{min(10, vagueness['vague_count'] * 2)} GEO points",
        })

    if not signals["people_behind"]["found"]:
        issues.append({
            "signal": "people_behind",
            "issue": "No visible team/expertise — AI cannot verify authority",
            "suggestion": "Add founder/team profiles with credentials and experience",
            "impact": "+4 GEO points",
        })

    return {
        "geo_entity_result": {
            "score": round(score, 1),
            "signals": signals,
            "issues": issues,
            "vagueness": vagueness,
        }
    }

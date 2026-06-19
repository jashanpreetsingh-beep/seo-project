"""
GEO Agent 3: Authority & Trust Score (20% of GEO Score).

Question: "Why should AI trust this website as a source?"

AI models weight authority signals heavily when deciding whether to cite or recommend.
This agent checks:
- Author profiles & credentials
- Reviews & testimonials
- Case studies & proof
- Awards & recognitions
- External mentions & backlink signals
- Publication history
- Professional affiliations
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState


def _check_author_signals(soup: BeautifulSoup, text: str) -> dict:
    """Check for author information and expertise signals."""
    result = {
        "has_author": False,
        "has_credentials": False,
        "has_author_bio": False,
        "has_author_image": False,
        "authors_found": [],
        "score": 0,
    }

    # Check for author schema
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        content = script.string or ""
        if '"author"' in content or '"Person"' in content:
            result["has_author"] = True
            result["score"] += 25

    # Check for author markup in HTML
    author_elements = soup.find_all(class_=re.compile(r'author|byline|written-by|post-author', re.I))
    if author_elements:
        result["has_author"] = True
        result["score"] += 20
        for elem in author_elements[:3]:
            author_text = elem.get_text(strip=True)[:100]
            if author_text:
                result["authors_found"].append(author_text)

    # Check for rel="author"
    author_links = soup.find_all("a", {"rel": "author"})
    if author_links:
        result["has_author"] = True
        result["score"] += 10

    # Credentials
    credential_patterns = [
        r'(?:PhD|Ph\.D|M\.D\.|MD|MBA|CPA|CFA|JD|J\.D\.)',
        r'(?:certified|licensed|registered|accredited)',
        r'(?:\d+\+?\s*years?\s*(?:of\s+)?experience)',
        r'(?:board[- ]certified|fellowship|residency)',
        r'(?:professor|researcher|scientist|specialist)',
    ]

    for pattern in credential_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            result["has_credentials"] = True
            result["score"] += 15
            break

    # Author bio section
    bio_elements = soup.find_all(class_=re.compile(r'bio|about-author|author-info|author-description', re.I))
    if bio_elements:
        result["has_author_bio"] = True
        result["score"] += 10

    # Author image
    author_imgs = soup.find_all("img", class_=re.compile(r'author|avatar|profile', re.I))
    if author_imgs:
        result["has_author_image"] = True
        result["score"] += 5

    result["score"] = min(100, result["score"])
    return result


def _check_social_proof(soup: BeautifulSoup, text: str) -> dict:
    """Check for reviews, testimonials, and social proof."""
    result = {
        "has_testimonials": False,
        "has_reviews": False,
        "has_ratings": False,
        "has_case_studies": False,
        "has_client_logos": False,
        "score": 0,
    }

    text_lower = text.lower()

    # Testimonials
    testimonial_signals = soup.find_all(class_=re.compile(r'testimonial|review|quote|feedback', re.I))
    if testimonial_signals:
        result["has_testimonials"] = True
        result["score"] += 25

    # Reviews/ratings patterns
    if re.search(r'(?:\d+\s*(?:reviews?|ratings?)|rated\s*\d|stars?|⭐)', text_lower):
        result["has_reviews"] = True
        result["score"] += 20

    # Aggregate rating schema
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        if script.string and "aggregateRating" in (script.string or ""):
            result["has_ratings"] = True
            result["score"] += 15

    # Case studies
    case_study_link = soup.find("a", href=re.compile(r'/case-stud|/success-stor|/portfolio', re.I))
    if case_study_link or "case study" in text_lower or "case studies" in text_lower:
        result["has_case_studies"] = True
        result["score"] += 20

    # Client logos
    client_sections = soup.find_all(class_=re.compile(r'client|partner|trusted|brand|logo', re.I))
    if client_sections:
        result["has_client_logos"] = True
        result["score"] += 10

    # Trust badges
    if re.search(r'(?:trusted by|used by|loved by)\s*[\d,]+', text_lower):
        result["score"] += 10

    result["score"] = min(100, result["score"])
    return result


def _check_recognition(soup: BeautifulSoup, text: str) -> dict:
    """Check for awards, media mentions, and external recognition."""
    result = {
        "has_awards": False,
        "has_media_mentions": False,
        "has_partnerships": False,
        "has_publications": False,
        "score": 0,
    }

    text_lower = text.lower()

    # Awards
    award_patterns = [
        r'(?:award|winner|finalist|nominated|recognized|honored)',
        r'(?:best of|top \d+|#\d+ in)',
        r'(?:inc\.\s*\d+|fortune|forbes|gartner)',
    ]
    for pattern in award_patterns:
        if re.search(pattern, text_lower):
            result["has_awards"] = True
            result["score"] += 25
            break

    # Media mentions
    media_patterns = [
        r'(?:as seen (?:on|in)|featured (?:on|in)|mentioned (?:on|in))',
        r'(?:press|media|news|coverage)',
        r'(?:TechCrunch|Forbes|Bloomberg|Reuters|NYT|BBC|CNN)',
    ]
    for pattern in media_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            result["has_media_mentions"] = True
            result["score"] += 25
            break

    # Partnerships
    if re.search(r'(?:partner|certified|authorized|official|approved)\s+(?:by|with|of)', text_lower):
        result["has_partnerships"] = True
        result["score"] += 15

    # Publications/research
    if re.search(r'(?:published|research|whitepaper|study|report|journal)', text_lower):
        result["has_publications"] = True
        result["score"] += 20

    result["score"] = min(100, result["score"])
    return result


def _check_trust_elements(soup: BeautifulSoup, url: str) -> dict:
    """Check for trust-building page elements."""
    result = {
        "has_contact_info": False,
        "has_physical_address": False,
        "has_privacy_policy": False,
        "has_terms": False,
        "has_about_page": False,
        "has_ssl": False,
        "score": 0,
    }

    # HTTPS
    if url.startswith("https://"):
        result["has_ssl"] = True
        result["score"] += 10

    # Contact info
    contact_link = soup.find("a", href=re.compile(r'/contact|mailto:', re.I))
    phone = soup.find(string=re.compile(r'[\+\(]?\d[\d\-\(\)\s]{8,}'))
    if contact_link or phone:
        result["has_contact_info"] = True
        result["score"] += 15

    # Physical address
    address_elem = soup.find(attrs={"itemprop": "address"}) or soup.find("address")
    if address_elem:
        result["has_physical_address"] = True
        result["score"] += 15

    # Privacy policy
    privacy_link = soup.find("a", href=re.compile(r'/privacy', re.I))
    if privacy_link:
        result["has_privacy_policy"] = True
        result["score"] += 10

    # Terms
    terms_link = soup.find("a", href=re.compile(r'/terms|/tos', re.I))
    if terms_link:
        result["has_terms"] = True
        result["score"] += 10

    # About page
    about_link = soup.find("a", href=re.compile(r'/about', re.I))
    if about_link:
        result["has_about_page"] = True
        result["score"] += 15

    result["score"] = min(100, result["score"])
    return result


async def authority_trust_node(state: SEOState) -> dict:
    """
    GEO Agent 3: Evaluate authority and trust signals for AI.

    Scoring (20% of total GEO):
    - Author signals: 30 pts
    - Social proof: 30 pts
    - Recognition: 20 pts
    - Trust elements: 20 pts
    """
    html = state.get("html", "")
    url = state.get("url", "")

    if not html:
        return {
            "geo_authority_result": {
                "score": 0,
                "author_signals": {},
                "social_proof": {},
                "recognition": {},
                "trust_elements": {},
                "issues": [],
            }
        }

    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)

    # Run checks
    author_signals = _check_author_signals(soup, text)
    social_proof = _check_social_proof(soup, text)
    recognition = _check_recognition(soup, text)
    trust_elements = _check_trust_elements(soup, url)

    # Calculate weighted score
    score = (
        author_signals["score"] * 0.30 +
        social_proof["score"] * 0.30 +
        recognition["score"] * 0.20 +
        trust_elements["score"] * 0.20
    )
    score = min(100, max(0, score))

    # Generate issues
    issues = []
    if author_signals["score"] < 30:
        issues.append({
            "signal": "author_authority",
            "issue": "No author profiles or credentials visible — AI cannot verify expertise",
            "suggestion": "Add author boxes with name, photo, credentials (PhD, years experience, certifications), and links to profiles",
            "impact": "+8 GEO points",
        })

    if social_proof["score"] < 25:
        issues.append({
            "signal": "social_proof",
            "issue": "Weak social proof — AI has no evidence of customer satisfaction",
            "suggestion": "Add testimonials with full names, case studies with measurable results, and aggregate ratings",
            "impact": "+7 GEO points",
        })

    if recognition["score"] < 20:
        issues.append({
            "signal": "recognition",
            "issue": "No external recognition signals",
            "suggestion": "Highlight awards, media mentions, partnerships, and published research",
            "impact": "+5 GEO points",
        })

    if trust_elements["score"] < 30:
        issues.append({
            "signal": "trust_elements",
            "issue": "Missing basic trust signals (contact, address, policies)",
            "suggestion": "Add contact page, physical address, privacy policy, and about page",
            "impact": "+4 GEO points",
        })

    if not author_signals["has_credentials"]:
        issues.append({
            "signal": "credentials",
            "issue": "No professional credentials mentioned",
            "suggestion": "Display relevant certifications, degrees, years of experience prominently",
            "impact": "+5 GEO points",
        })

    return {
        "geo_authority_result": {
            "score": round(score, 1),
            "author_signals": author_signals,
            "social_proof": social_proof,
            "recognition": recognition,
            "trust_elements": trust_elements,
            "issues": issues,
        }
    }

"""
GEO Agent 4: Citation Probability Score (15% of GEO Score).

Question: "Would an AI model cite this website as a source?"

AI prefers to cite:
- Original research & data
- Unique statistics
- Expert opinions with named sources
- Detailed guides (comprehensive, not superficial)
- First-party data and case studies
- Industry benchmarks

Weak: "SEO is important for businesses"
Strong: "Based on our analysis of 500 websites, pages with FAQ schema
         received 32% more AI citation impressions in Q1 2024"
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState


def _check_original_research(soup: BeautifulSoup, text: str) -> dict:
    """Check for original research, data, and unique insights."""
    result = {
        "has_original_data": False,
        "has_research": False,
        "has_methodology": False,
        "data_signals": [],
        "score": 0,
    }

    text_lower = text.lower()

    # Original research signals
    research_patterns = [
        (r'(?:our|we)\s+(?:research|study|analysis|survey|data)\s+(?:shows?|found|reveals?|indicates?)', "First-party research claim"),
        (r'(?:we\s+(?:analyzed|surveyed|studied|examined|tested))\s+\d+', "Quantified research"),
        (r'(?:based on|according to)\s+(?:our|internal)\s+(?:data|research|analysis)', "Internal data reference"),
        (r'(?:methodology|sample size|data collection|survey of)', "Research methodology"),
    ]

    for pattern, label in research_patterns:
        if re.search(pattern, text_lower):
            result["data_signals"].append(label)

    if len(result["data_signals"]) >= 2:
        result["has_original_data"] = True
        result["has_research"] = True
        result["score"] += 45
    elif len(result["data_signals"]) >= 1:
        result["has_research"] = True
        result["score"] += 25

    # Check for methodology section
    if re.search(r'(?:methodology|how we measured|our approach|data sources)', text_lower):
        result["has_methodology"] = True
        result["score"] += 15

    result["score"] = min(100, result["score"])
    return result


def _check_statistics_quality(text: str) -> dict:
    """Evaluate the quality and density of statistics in content."""
    result = {
        "stat_count": 0,
        "has_sourced_stats": False,
        "has_specific_numbers": False,
        "has_year_references": False,
        "stat_examples": [],
        "score": 0,
    }

    # Find statistics patterns
    stat_patterns = [
        r'\d+(?:\.\d+)?%\s+(?:of|increase|decrease|growth|more|less|higher|lower)',
        r'(?:\$|£|€)[\d,.]+(?:\s*(?:million|billion|M|B|K))?',
        r'\d+(?:,\d{3})+\s+(?:users|customers|companies|downloads|transactions)',
        r'(?:\d+x|\d+X)\s+(?:more|faster|better|increase|growth)',
    ]

    stats_found = []
    for pattern in stat_patterns:
        matches = re.findall(pattern, text)
        stats_found.extend(matches)

    result["stat_count"] = len(stats_found)
    result["stat_examples"] = stats_found[:5]

    if len(stats_found) >= 5:
        result["has_specific_numbers"] = True
        result["score"] += 35
    elif len(stats_found) >= 2:
        result["has_specific_numbers"] = True
        result["score"] += 20

    # Check for sourced statistics
    source_patterns = [
        r'(?:source|according to|research by|data from|study by)\s*:?\s*[\w\s]+(?:\d{4})?',
        r'\([\w\s]+,?\s*\d{4}\)',  # Academic citation style
    ]
    for pattern in source_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            result["has_sourced_stats"] = True
            result["score"] += 20
            break

    # Year references (freshness)
    current_year_patterns = [r'202[4-6]', r'(?:this year|latest|recent|current)']
    for pattern in current_year_patterns:
        if re.search(pattern, text):
            result["has_year_references"] = True
            result["score"] += 10
            break

    result["score"] = min(100, result["score"])
    return result


def _check_unique_insights(soup: BeautifulSoup, text: str) -> dict:
    """Check for unique expert opinions and insights."""
    result = {
        "has_expert_quotes": False,
        "has_unique_frameworks": False,
        "has_predictions": False,
        "has_contrarian_views": False,
        "score": 0,
    }

    # Expert quotes
    blockquotes = soup.find_all("blockquote")
    quote_patterns = [
        r'(?:says?|according to|explains?|notes?)\s+[\w\s]+(?:,\s*(?:CEO|CTO|founder|director|professor))',
        r'"[^"]{20,200}"',
    ]

    if blockquotes:
        result["has_expert_quotes"] = True
        result["score"] += 20

    for pattern in quote_patterns:
        if re.search(pattern, text):
            result["has_expert_quotes"] = True
            result["score"] += 15
            break

    # Unique frameworks or models
    framework_patterns = [
        r'(?:our|the)\s+\w+\s+(?:framework|model|method|approach|formula|system)',
        r'(?:we call this|we developed|our proprietary)',
    ]
    for pattern in framework_patterns:
        if re.search(pattern, text.lower()):
            result["has_unique_frameworks"] = True
            result["score"] += 20
            break

    # Predictions / forward-looking
    if re.search(r'(?:predict|forecast|expect|anticipate|trend|future|202[5-9])', text.lower()):
        result["has_predictions"] = True
        result["score"] += 10

    # Contrarian / unique perspective
    contrarian_patterns = [
        r'(?:contrary to|unlike|while most|the truth is|misconception|myth)',
        r'(?:actually|however|counterintuitive|surprisingly)',
    ]
    for pattern in contrarian_patterns:
        if re.search(pattern, text.lower()):
            result["has_contrarian_views"] = True
            result["score"] += 15
            break

    result["score"] = min(100, result["score"])
    return result


def _check_content_depth(text: str, soup: BeautifulSoup) -> dict:
    """Check if content is comprehensive enough to be citation-worthy."""
    result = {
        "word_count": 0,
        "heading_count": 0,
        "is_comprehensive": False,
        "has_conclusion": False,
        "score": 0,
    }

    words = text.split()
    result["word_count"] = len(words)

    headings = soup.find_all(["h2", "h3"])
    result["heading_count"] = len(headings)

    # Comprehensive content (long-form with structure)
    if len(words) >= 2000 and len(headings) >= 5:
        result["is_comprehensive"] = True
        result["score"] += 40
    elif len(words) >= 1000 and len(headings) >= 3:
        result["is_comprehensive"] = True
        result["score"] += 25
    elif len(words) >= 500:
        result["score"] += 10

    # Conclusion/summary
    if re.search(r'(?:conclusion|summary|key takeaway|final thought|wrapping up|in summary)', text.lower()):
        result["has_conclusion"] = True
        result["score"] += 15

    result["score"] = min(100, result["score"])
    return result


async def citation_probability_node(state: SEOState) -> dict:
    """
    GEO Agent 4: Evaluate probability that AI would cite this page.

    Scoring (15% of total GEO):
    - Original research: 30 pts
    - Statistics quality: 25 pts
    - Unique insights: 25 pts
    - Content depth: 20 pts
    """
    html = state.get("html", "")

    if not html:
        return {
            "geo_citation_result": {
                "score": 0,
                "original_research": {},
                "statistics": {},
                "unique_insights": {},
                "content_depth": {},
                "issues": [],
            }
        }

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    soup_full = BeautifulSoup(html, "lxml")

    # Run checks
    original_research = _check_original_research(soup_full, text)
    statistics = _check_statistics_quality(text)
    unique_insights = _check_unique_insights(soup_full, text)
    content_depth = _check_content_depth(text, soup_full)

    # Calculate weighted score
    score = (
        original_research["score"] * 0.30 +
        statistics["score"] * 0.25 +
        unique_insights["score"] * 0.25 +
        content_depth["score"] * 0.20
    )
    score = min(100, max(0, score))

    # Generate issues
    issues = []
    if original_research["score"] < 25:
        issues.append({
            "signal": "original_research",
            "issue": "No original research or first-party data — AI has nothing unique to cite",
            "suggestion": "Publish original research: surveys, data analyses, case study results with specific numbers",
            "impact": "+12 GEO points",
        })

    if statistics["score"] < 20:
        issues.append({
            "signal": "statistics",
            "issue": "Few specific statistics — content is opinion-based rather than data-backed",
            "suggestion": "Add sourced statistics, benchmarks, and quantified results throughout your content",
            "impact": "+8 GEO points",
        })

    if unique_insights["score"] < 20:
        issues.append({
            "signal": "unique_insights",
            "issue": "No unique expert insights or frameworks",
            "suggestion": "Develop proprietary frameworks, share expert opinions with credentials, add unique angles AI cannot find elsewhere",
            "impact": "+7 GEO points",
        })

    if content_depth["score"] < 20:
        issues.append({
            "signal": "content_depth",
            "issue": "Content lacks depth for citation-worthiness",
            "suggestion": "Create comprehensive, long-form content (2000+ words) with clear sections and conclusions",
            "impact": "+6 GEO points",
        })

    if not statistics.get("has_sourced_stats"):
        issues.append({
            "signal": "sourced_stats",
            "issue": "Statistics not sourced — reduces AI trust in your data",
            "suggestion": "Add citations: 'According to [Source, Year]...' or link to original data",
            "impact": "+4 GEO points",
        })

    return {
        "geo_citation_result": {
            "score": round(score, 1),
            "original_research": original_research,
            "statistics": statistics,
            "unique_insights": unique_insights,
            "content_depth": content_depth,
            "issues": issues,
        }
    }

"""
GEO Agent 2: AI Answer Extraction Score (25% of GEO Score).

Question: "Can AI easily extract direct answers from this website?"

AI models prefer:
- FAQ sections with clear Q&A pairs
- How-to guides with steps
- Comparison pages with tables
- Definitions with clear structure
- Step-by-step content
- Data tables
- Concrete examples

If content says "Premium dental services" — AI cannot answer
"How much do dental implants cost?" from this page.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState


def _check_faq_content(soup: BeautifulSoup, text: str) -> dict:
    """Check for FAQ-style question-answer content."""
    result = {
        "has_faq_section": False,
        "has_faq_schema": False,
        "question_count": 0,
        "questions_found": [],
        "score": 0,
    }

    # Check for FAQ schema
    scripts = soup.find_all("script", {"type": "application/ld+json"})
    for script in scripts:
        if script.string and "FAQPage" in (script.string or ""):
            result["has_faq_schema"] = True
            result["score"] += 30

    # Check for question patterns in headings
    question_patterns = [
        r'^(what|how|why|when|where|which|who|can|does|is|are|should|will)\s',
        r'\?$',
    ]

    headings = soup.find_all(["h2", "h3", "h4"])
    questions = []
    for h in headings:
        h_text = h.get_text(strip=True)
        for pattern in question_patterns:
            if re.search(pattern, h_text, re.IGNORECASE):
                questions.append(h_text)
                break

    result["questions_found"] = questions[:10]
    result["question_count"] = len(questions)

    if len(questions) >= 5:
        result["has_faq_section"] = True
        result["score"] += 40
    elif len(questions) >= 2:
        result["has_faq_section"] = True
        result["score"] += 20

    # Check for dedicated FAQ page link
    faq_link = soup.find("a", href=re.compile(r"/faq|/frequently-asked|/questions", re.I))
    if faq_link:
        result["score"] += 10

    return result


def _check_howto_content(soup: BeautifulSoup, text: str) -> dict:
    """Check for how-to/step-by-step content."""
    result = {
        "has_steps": False,
        "has_numbered_list": False,
        "has_process_content": False,
        "step_count": 0,
        "score": 0,
    }

    # Check for ordered lists
    ordered_lists = soup.find_all("ol")
    if ordered_lists:
        total_items = sum(len(ol.find_all("li")) for ol in ordered_lists)
        if total_items >= 3:
            result["has_numbered_list"] = True
            result["has_steps"] = True
            result["step_count"] = total_items
            result["score"] += 25

    # Check for step patterns in content
    step_patterns = [
        r'step\s*\d+',
        r'(?:first|second|third|fourth|fifth|next|then|finally)',
        r'(?:phase|stage)\s*\d+',
    ]

    for pattern in step_patterns:
        matches = re.findall(pattern, text.lower())
        if len(matches) >= 3:
            result["has_process_content"] = True
            result["score"] += 20
            break

    # Check for how-to headings
    howto_headings = soup.find_all(["h1", "h2", "h3"], string=re.compile(r'how to|guide|tutorial|steps', re.I))
    if howto_headings:
        result["score"] += 15

    return result


def _check_comparison_content(soup: BeautifulSoup, text: str) -> dict:
    """Check for comparison/versus content with tables."""
    result = {
        "has_tables": False,
        "has_comparison": False,
        "table_count": 0,
        "score": 0,
    }

    # Check for data tables
    tables = soup.find_all("table")
    if tables:
        result["has_tables"] = True
        result["table_count"] = len(tables)
        result["score"] += 20

    # Check for comparison patterns
    comparison_patterns = [
        r'(?:vs\.?|versus|compared to|comparison|difference between)',
        r'(?:pros and cons|advantages|disadvantages|benefits)',
        r'(?:best|top \d+|alternatives)',
    ]

    for pattern in comparison_patterns:
        if re.search(pattern, text.lower()):
            result["has_comparison"] = True
            result["score"] += 15
            break

    return result


def _check_definitions(soup: BeautifulSoup, text: str) -> dict:
    """Check for clear definitions and explanations."""
    result = {
        "has_definitions": False,
        "definition_count": 0,
        "score": 0,
    }

    # Check for definition patterns
    definition_patterns = [
        r'(?:is defined as|refers to|means that|is a type of)',
        r'(?:what is|definition of)',
        r'(?:\w+)\s+is\s+(?:a|an|the)\s+(?:\w+\s+){1,5}(?:that|which|used|designed)',
    ]

    definition_count = 0
    for pattern in definition_patterns:
        matches = re.findall(pattern, text.lower())
        definition_count += len(matches)

    if definition_count >= 3:
        result["has_definitions"] = True
        result["definition_count"] = definition_count
        result["score"] += 30
    elif definition_count >= 1:
        result["has_definitions"] = True
        result["definition_count"] = definition_count
        result["score"] += 15

    # Check for <dl> (definition list) elements
    dl_elements = soup.find_all("dl")
    if dl_elements:
        result["score"] += 15

    return result


def _check_data_richness(soup: BeautifulSoup, text: str) -> dict:
    """Check for data, statistics, and concrete numbers."""
    result = {
        "has_statistics": False,
        "has_specific_numbers": False,
        "data_points": 0,
        "score": 0,
    }

    # Check for statistics and numbers
    stat_patterns = [
        r'\d+%',  # Percentages
        r'\$[\d,]+',  # Dollar amounts
        r'[\d,]+\s*(?:users|customers|clients|downloads|reviews)',  # User counts
        r'(?:increased|decreased|grew|reduced)\s+(?:by\s+)?\d+',  # Growth metrics
    ]

    data_points = 0
    for pattern in stat_patterns:
        matches = re.findall(pattern, text)
        data_points += len(matches)

    if data_points >= 5:
        result["has_statistics"] = True
        result["has_specific_numbers"] = True
        result["data_points"] = data_points
        result["score"] += 35
    elif data_points >= 2:
        result["has_specific_numbers"] = True
        result["data_points"] = data_points
        result["score"] += 15

    return result


def _check_content_structure(soup: BeautifulSoup) -> dict:
    """Check if content is well-structured for AI parsing."""
    result = {
        "has_clear_sections": False,
        "has_summary": False,
        "has_bullet_points": False,
        "score": 0,
    }

    # Check heading count
    headings = soup.find_all(["h2", "h3"])
    if len(headings) >= 3:
        result["has_clear_sections"] = True
        result["score"] += 15

    # Check for unordered/ordered lists
    lists = soup.find_all(["ul", "ol"])
    total_items = sum(len(l.find_all("li")) for l in lists)
    if total_items >= 5:
        result["has_bullet_points"] = True
        result["score"] += 15

    # Check for summary/TL;DR
    summary_patterns = soup.find_all(string=re.compile(r'(?:summary|tl;?dr|key takeaway|in brief|overview)', re.I))
    if summary_patterns:
        result["has_summary"] = True
        result["score"] += 20

    return result


async def answer_extraction_node(state: SEOState) -> dict:
    """
    GEO Agent 2: Evaluate how easily AI can extract answers from content.

    Scoring (25% of total GEO):
    - FAQ content: 25 pts
    - How-to/step content: 20 pts
    - Comparison/tables: 15 pts
    - Definitions: 15 pts
    - Data richness: 15 pts
    - Content structure: 10 pts
    """
    html = state.get("html", "")

    if not html:
        return {
            "geo_answer_result": {
                "score": 0,
                "faq": {},
                "howto": {},
                "comparison": {},
                "definitions": {},
                "data_richness": {},
                "structure": {},
                "issues": [],
            }
        }

    soup = BeautifulSoup(html, "lxml")
    # Get text for pattern matching
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    # Re-parse for structure checks
    soup_full = BeautifulSoup(html, "lxml")

    # Run all checks
    faq = _check_faq_content(soup_full, text)
    howto = _check_howto_content(soup_full, text)
    comparison = _check_comparison_content(soup_full, text)
    definitions = _check_definitions(soup_full, text)
    data_richness = _check_data_richness(soup_full, text)
    structure = _check_content_structure(soup_full)

    # Calculate weighted score
    component_weights = {
        "faq": 0.25,
        "howto": 0.20,
        "comparison": 0.15,
        "definitions": 0.15,
        "data_richness": 0.15,
        "structure": 0.10,
    }

    components = {
        "faq": faq,
        "howto": howto,
        "comparison": comparison,
        "definitions": definitions,
        "data_richness": data_richness,
        "structure": structure,
    }

    score = sum(
        min(100, components[k]["score"]) * component_weights[k]
        for k in component_weights
    )
    score = min(100, max(0, score))

    # Generate issues
    issues = []
    if faq["score"] < 20:
        issues.append({
            "signal": "faq_content",
            "issue": "No FAQ content — AI cannot extract direct answers",
            "suggestion": "Add FAQ section with 5-10 common questions your audience asks. Use question-based headings (H2/H3)",
            "impact": "+10 GEO points",
        })

    if howto["score"] < 15:
        issues.append({
            "signal": "howto_content",
            "issue": "No step-by-step or how-to content",
            "suggestion": "Create how-to guides with numbered steps for processes related to your service",
            "impact": "+7 GEO points",
        })

    if comparison["score"] < 10:
        issues.append({
            "signal": "comparison_content",
            "issue": "No comparison or tabular data",
            "suggestion": "Add comparison tables, pricing tables, or feature matrices that AI can easily parse",
            "impact": "+5 GEO points",
        })

    if data_richness["score"] < 15:
        issues.append({
            "signal": "data_richness",
            "issue": "Content lacks specific data, numbers, and statistics",
            "suggestion": "Add concrete numbers: costs, timeframes, success rates, user counts. AI prefers specific over vague",
            "impact": "+8 GEO points",
        })

    if structure["score"] < 15:
        issues.append({
            "signal": "content_structure",
            "issue": "Content poorly structured for AI parsing",
            "suggestion": "Use clear H2/H3 sections, bullet points, and add a summary/key takeaways section",
            "impact": "+5 GEO points",
        })

    return {
        "geo_answer_result": {
            "score": round(score, 1),
            "faq": faq,
            "howto": howto,
            "comparison": comparison,
            "definitions": definitions,
            "data_richness": data_richness,
            "structure": structure,
            "issues": issues,
        }
    }

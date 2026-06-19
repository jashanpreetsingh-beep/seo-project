"""
GEO Agent 5: Conversational Search Score (15% of GEO Score).

Question: "Does content match how humans ask AI questions?"

Users ask AI:
- "What is the best..."
- "How do I..."
- "Compare X vs Y"
- "Which one should I choose..."
- "How much does X cost..."
- "Is X worth it..."

This agent checks whether the website has content that directly
answers the natural language queries users ask AI about this niche.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState


# Common conversational query patterns by intent type
QUERY_PATTERNS = {
    "informational": [
        r'what is\s+\w+',
        r'how does\s+\w+\s+work',
        r'what are\s+(?:the\s+)?(?:benefits|features|advantages)',
        r'why\s+(?:is|are|should)',
        r'when\s+(?:should|to|is)',
    ],
    "commercial": [
        r'best\s+\w+\s+(?:for|in|under)',
        r'top\s+\d+\s+\w+',
        r'(?:compare|vs|versus)',
        r'(?:review|rating|worth)',
        r'how much\s+(?:does|is|do)',
        r'(?:pricing|cost|price)\s+(?:of|for)',
    ],
    "transactional": [
        r'(?:buy|purchase|order|get|subscribe)',
        r'(?:free trial|demo|sign up)',
        r'(?:discount|coupon|deal)',
    ],
    "navigational": [
        r'(?:contact|reach|find|location|hours|support)',
        r'(?:login|sign in|my account)',
    ],
}


def _detect_site_queries(soup: BeautifulSoup, text: str, url: str) -> dict:
    """Detect what queries users might ask AI about this type of site."""
    result = {
        "likely_queries": [],
        "query_types_covered": [],
        "query_types_missing": [],
        "industry_detected": "",
    }

    text_lower = text.lower()

    # Detect industry/niche for query suggestions
    industry_queries = {
        "technology": [
            "What is [product]?", "How does [product] work?",
            "Best [product type] for [use case]",
            "[Product] vs [competitor]", "Is [product] worth it?",
            "How much does [product] cost?",
        ],
        "healthcare": [
            "How much does [procedure] cost?",
            "What are the risks of [procedure]?",
            "Best [specialist] near me",
            "How long does [procedure] take to recover?",
            "[Treatment A] vs [Treatment B]",
        ],
        "ecommerce": [
            "Best [product] under $[price]",
            "[Product] review", "Is [product] worth buying?",
            "[Product A] vs [Product B]",
            "Where to buy [product]?",
        ],
        "marketing": [
            "Best [service] agency", "How much does [service] cost?",
            "What is [marketing term]?", "[Strategy A] vs [Strategy B]",
            "How to improve [metric]",
        ],
        "education": [
            "Best [course type] courses",
            "Is [certification] worth it?",
            "How long to learn [skill]?",
            "[Course A] vs [Course B]",
        ],
    }

    # Simple industry detection from content
    detected_industry = "general"
    industry_signals = {
        "technology": ["software", "platform", "api", "integration", "saas"],
        "healthcare": ["health", "medical", "patient", "treatment", "diagnosis"],
        "ecommerce": ["product", "shop", "cart", "price", "delivery"],
        "marketing": ["marketing", "seo", "campaign", "analytics", "content"],
        "education": ["course", "learn", "student", "training", "certification"],
    }

    for ind, signals in industry_signals.items():
        if sum(1 for s in signals if s in text_lower) >= 2:
            detected_industry = ind
            break

    result["industry_detected"] = detected_industry
    if detected_industry in industry_queries:
        result["likely_queries"] = industry_queries[detected_industry]

    return result


def _check_query_coverage(soup: BeautifulSoup, text: str) -> dict:
    """Check how well content covers different query intents."""
    result = {
        "informational_coverage": 0,
        "commercial_coverage": 0,
        "transactional_coverage": 0,
        "navigational_coverage": 0,
        "total_coverage": 0,
        "covered_patterns": [],
        "score": 0,
    }

    text_lower = text.lower()

    # Check each query type
    for qtype, patterns in QUERY_PATTERNS.items():
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matches += 1

        coverage = min(100, matches * 25)
        result[f"{qtype}_coverage"] = coverage

    # Calculate total coverage
    coverages = [
        result["informational_coverage"],
        result["commercial_coverage"],
        result["transactional_coverage"],
        result["navigational_coverage"],
    ]
    result["total_coverage"] = sum(coverages) / 4

    # Score based on coverage
    if result["total_coverage"] >= 60:
        result["score"] = 80
    elif result["total_coverage"] >= 40:
        result["score"] = 60
    elif result["total_coverage"] >= 20:
        result["score"] = 40
    else:
        result["score"] = 15

    return result


def _check_question_headings(soup: BeautifulSoup) -> dict:
    """Check if headings are phrased as questions (matches AI query patterns)."""
    result = {
        "total_headings": 0,
        "question_headings": 0,
        "question_ratio": 0,
        "questions_found": [],
        "score": 0,
    }

    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    result["total_headings"] = len(headings)

    question_words = ["what", "how", "why", "when", "where", "which", "who", "can", "does", "is", "are", "should", "will"]

    for h in headings:
        h_text = h.get_text(strip=True)
        h_lower = h_text.lower()
        if h_text.endswith("?") or any(h_lower.startswith(qw + " ") for qw in question_words):
            result["question_headings"] += 1
            result["questions_found"].append(h_text[:80])

    if result["total_headings"] > 0:
        result["question_ratio"] = result["question_headings"] / result["total_headings"]

    if result["question_headings"] >= 5:
        result["score"] = 90
    elif result["question_headings"] >= 3:
        result["score"] = 70
    elif result["question_headings"] >= 1:
        result["score"] = 40
    else:
        result["score"] = 10

    return result


def _check_conversational_tone(text: str) -> dict:
    """Check if content uses conversational, AI-friendly language."""
    result = {
        "has_direct_address": False,
        "has_question_answers": False,
        "has_simple_language": False,
        "score": 0,
    }

    text_lower = text.lower()

    # Direct address (you/your)
    you_count = len(re.findall(r'\byou(?:r|\'re|\'ll)?\b', text_lower))
    if you_count >= 5:
        result["has_direct_address"] = True
        result["score"] += 25

    # Q&A pattern in text
    qa_pattern = r'(?:^|\n)\s*(?:Q:|Question:|\w+\?)\s*\n?\s*(?:A:|Answer:)'
    if re.search(qa_pattern, text, re.IGNORECASE | re.MULTILINE):
        result["has_question_answers"] = True
        result["score"] += 30

    # Self-answering pattern: Question heading followed by paragraph
    question_answer_pairs = re.findall(
        r'(?:what|how|why|when|which|who)[^\n?]*\?[^\n]*\n[^\n]{50,}',
        text_lower
    )
    if question_answer_pairs:
        result["has_question_answers"] = True
        result["score"] += 25

    # Simple language check (short sentences)
    sentences = re.split(r'[.!?]+', text)
    if sentences:
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_length < 20:
            result["has_simple_language"] = True
            result["score"] += 20

    result["score"] = min(100, result["score"])
    return result


def _check_long_tail_coverage(soup: BeautifulSoup, text: str) -> dict:
    """Check for long-tail conversational content."""
    result = {
        "has_comparison_pages": False,
        "has_cost_content": False,
        "has_best_of_content": False,
        "has_alternative_content": False,
        "coverage_items": [],
        "score": 0,
    }

    text_lower = text.lower()

    # Cost/pricing content
    if re.search(r'(?:how much|cost|pricing|price|rates?|fee)', text_lower):
        result["has_cost_content"] = True
        result["coverage_items"].append("cost/pricing")
        result["score"] += 25

    # Comparison content
    if re.search(r'(?:vs\.?|versus|compared|comparison|difference|better)', text_lower):
        result["has_comparison_pages"] = True
        result["coverage_items"].append("comparisons")
        result["score"] += 25

    # Best-of / recommendation content
    if re.search(r'(?:best|top\s+\d|recommended|our pick|editor.?s? choice)', text_lower):
        result["has_best_of_content"] = True
        result["coverage_items"].append("best-of/recommendations")
        result["score"] += 25

    # Alternatives content
    if re.search(r'(?:alternative|instead of|similar to|like \w+ but|competitor)', text_lower):
        result["has_alternative_content"] = True
        result["coverage_items"].append("alternatives")
        result["score"] += 25

    result["score"] = min(100, result["score"])
    return result


async def conversational_search_node(state: SEOState) -> dict:
    """
    GEO Agent 5: Evaluate alignment with conversational AI queries.

    Scoring (15% of total GEO):
    - Query coverage: 25 pts
    - Question headings: 25 pts
    - Conversational tone: 25 pts
    - Long-tail coverage: 25 pts
    """
    html = state.get("html", "")
    url = state.get("url", "")

    if not html:
        return {
            "geo_conversational_result": {
                "score": 0,
                "site_queries": {},
                "query_coverage": {},
                "question_headings": {},
                "conversational_tone": {},
                "long_tail": {},
                "issues": [],
            }
        }

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)

    soup_full = BeautifulSoup(html, "lxml")

    # Run checks
    site_queries = _detect_site_queries(soup_full, text, url)
    query_coverage = _check_query_coverage(soup_full, text)
    question_headings = _check_question_headings(soup_full)
    conversational_tone = _check_conversational_tone(text)
    long_tail = _check_long_tail_coverage(soup_full, text)

    # Calculate weighted score
    score = (
        query_coverage["score"] * 0.25 +
        question_headings["score"] * 0.25 +
        conversational_tone["score"] * 0.25 +
        long_tail["score"] * 0.25
    )
    score = min(100, max(0, score))

    # Generate issues
    issues = []
    if question_headings["score"] < 40:
        issues.append({
            "signal": "question_headings",
            "issue": "Headings don't match how people ask AI questions",
            "suggestion": "Rewrite headings as questions: 'How much does X cost?', 'What is the best Y for Z?', 'How do I...'",
            "impact": "+6 GEO points",
        })

    if long_tail["score"] < 25:
        issues.append({
            "signal": "long_tail_content",
            "issue": "Missing long-tail conversational content",
            "suggestion": f"Create content for queries your audience asks AI: {', '.join(site_queries.get('likely_queries', [])[:3])}",
            "impact": "+8 GEO points",
        })

    if conversational_tone["score"] < 30:
        issues.append({
            "signal": "conversational_tone",
            "issue": "Content tone is too formal/corporate for AI extraction",
            "suggestion": "Write in a direct, conversational style. Use 'you/your', answer questions directly, keep sentences short",
            "impact": "+5 GEO points",
        })

    if query_coverage["informational_coverage"] < 25:
        issues.append({
            "signal": "informational_queries",
            "issue": "Weak coverage of 'what is' and 'how does' queries",
            "suggestion": "Add educational content that explains concepts, processes, and definitions in your niche",
            "impact": "+4 GEO points",
        })

    if not long_tail.get("has_comparison_pages"):
        issues.append({
            "signal": "comparison_content",
            "issue": "No comparison content — users ask AI 'X vs Y' frequently",
            "suggestion": "Create comparison pages for your product/service vs competitors or alternatives",
            "impact": "+5 GEO points",
        })

    return {
        "geo_conversational_result": {
            "score": round(score, 1),
            "site_queries": site_queries,
            "query_coverage": query_coverage,
            "question_headings": question_headings,
            "conversational_tone": conversational_tone,
            "long_tail": long_tail,
            "issues": issues,
        }
    }

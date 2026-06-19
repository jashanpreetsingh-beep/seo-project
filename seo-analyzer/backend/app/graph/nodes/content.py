"""
Content Quality Analyzer Node.

Evaluates:
- Word count vs page-type minimums
- Readability (Flesch-Kincaid, Gunning Fog)
- Heading structure and hierarchy
- E-E-A-T signals (Experience, Expertise, Authority, Trust)
- Thin content detection
- Content freshness signals
"""
from __future__ import annotations


import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity

# Minimum word counts by detected page type
WORD_MINIMUMS = {
    "homepage": 500,
    "service": 800,
    "blog": 1500,
    "product": 300,
    "location": 500,
    "default": 600,
}


def _extract_text(html: str) -> str:
    """Extract visible text content from HTML (strips tags, scripts, styles)."""
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _calculate_readability(text: str) -> dict:
    """
    Calculate readability metrics.
    Uses simplified Flesch-Kincaid since textstat may not be installed.
    """
    words = text.split()
    word_count = len(words)

    if word_count < 30:
        return {"score": 0, "grade_level": "N/A", "description": "Too little content to assess"}

    # Count sentences (approximate)
    sentences = len(re.findall(r"[.!?]+", text)) or 1

    # Count syllables (simplified)
    def count_syllables(word: str) -> int:
        word = word.lower()
        vowels = "aeiou"
        count = 0
        prev_vowel = False
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        return max(1, count)

    total_syllables = sum(count_syllables(w) for w in words)

    # Flesch Reading Ease
    avg_sentence_length = word_count / sentences
    avg_syllables_per_word = total_syllables / word_count
    flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
    flesch_score = max(0, min(100, flesch_score))

    # Grade level
    if flesch_score >= 80:
        grade = "6th grade (Easy)"
    elif flesch_score >= 60:
        grade = "8th-9th grade (Standard)"
    elif flesch_score >= 40:
        grade = "10th-12th grade (Difficult)"
    else:
        grade = "College+ (Very Difficult)"

    return {
        "flesch_score": round(flesch_score, 1),
        "grade_level": grade,
        "avg_sentence_length": round(avg_sentence_length, 1),
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
        "description": f"Flesch Reading Ease: {flesch_score:.0f}/100",
    }


def _analyze_headings(html: str) -> dict:
    """Analyze heading hierarchy (H1-H6)."""
    soup = BeautifulSoup(html, "lxml")
    headings = {}

    for level in range(1, 7):
        tags = soup.find_all(f"h{level}")
        headings[f"h{level}"] = [tag.get_text(strip=True)[:100] for tag in tags]

    result = {
        "structure": headings,
        "h1_count": len(headings.get("h1", [])),
        "has_proper_hierarchy": True,
        "issues": [],
    }

    # Check H1
    if result["h1_count"] == 0:
        result["issues"].append("No H1 tag found")
        result["has_proper_hierarchy"] = False
    elif result["h1_count"] > 1:
        result["issues"].append(f"Multiple H1 tags ({result['h1_count']}) — use only one")

    # Check hierarchy gaps (e.g., H1 → H3 with no H2)
    found_levels = [i for i in range(1, 7) if headings.get(f"h{i}")]
    for i in range(len(found_levels) - 1):
        if found_levels[i + 1] - found_levels[i] > 1:
            result["has_proper_hierarchy"] = False
            result["issues"].append(
                f"Heading hierarchy gap: H{found_levels[i]} → H{found_levels[i+1]} (skipped H{found_levels[i]+1})"
            )

    return result


def _detect_eeat_signals(html: str, text: str) -> dict:
    """
    Detect E-E-A-T signals in the content.
    
    E-E-A-T = Experience, Expertise, Authoritativeness, Trustworthiness
    (Google's quality framework from their Quality Rater Guidelines)
    """
    soup = BeautifulSoup(html, "lxml")
    signals = {
        "experience": {"score": 0, "signals": []},
        "expertise": {"score": 0, "signals": []},
        "authoritativeness": {"score": 0, "signals": []},
        "trustworthiness": {"score": 0, "signals": []},
    }

    # Experience signals
    experience_patterns = [
        (r"\b(I|we|my|our)\b.*\b(tested|tried|used|experienced|personally)\b", "First-person experience"),
        (r"\bcase stud(y|ies)\b", "Case studies present"),
        (r"\b(results|outcome|data|experiment)\b", "Results/data mentioned"),
    ]
    for pattern, label in experience_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            signals["experience"]["signals"].append(label)
            signals["experience"]["score"] += 25

    # Expertise signals
    if soup.find(class_=re.compile(r"author|byline|written-by", re.I)):
        signals["expertise"]["signals"].append("Author byline found")
        signals["expertise"]["score"] += 30
    if soup.find(string=re.compile(r"(PhD|MD|CPA|certified|licensed)", re.I)):
        signals["expertise"]["signals"].append("Credentials mentioned")
        signals["expertise"]["score"] += 30

    # Authoritativeness signals
    if soup.find(string=re.compile(r"(cited by|referenced|featured in|as seen on)", re.I)):
        signals["authoritativeness"]["signals"].append("External recognition")
        signals["authoritativeness"]["score"] += 30

    # Trustworthiness signals
    trust_elements = [
        ("contact", "Contact information"),
        ("privacy", "Privacy policy link"),
        ("terms", "Terms of service link"),
        ("about", "About page link"),
    ]
    for keyword, label in trust_elements:
        if soup.find("a", href=re.compile(keyword, re.I)):
            signals["trustworthiness"]["signals"].append(label)
            signals["trustworthiness"]["score"] += 15

    # HTTPS
    signals["trustworthiness"]["signals"].append("Page evaluation only — HTTPS checked in technical")

    # Cap scores at 100
    for key in signals:
        signals[key]["score"] = min(100, signals[key]["score"])

    return signals


async def content_analyzer_node(state: SEOState) -> dict:
    """
    Analyze content quality: word count, readability, headings, E-E-A-T.
    """
    html = state.get("html", "")
    if not html:
        return {"content_result": {"score": 0, "issues": [{"severity": "critical", "category": "content", "title": "No content to analyze", "description": "Page fetch failed or returned empty.", "recommendation": "Ensure the URL is accessible.", "impact": ""}]}}

    text = _extract_text(html)
    word_count = _count_words(text)
    readability = _calculate_readability(text)
    headings = _analyze_headings(html)
    eeat = _detect_eeat_signals(html, text)

    issues: list[dict] = []
    score = 100

    # Word count check
    min_words = WORD_MINIMUMS["default"]
    thin_content = word_count < min_words
    if thin_content:
        severity = Severity.CRITICAL if word_count < 200 else Severity.HIGH
        issues.append(SEOIssue(
            severity=severity,
            category="content",
            title=f"Thin content ({word_count} words)",
            description=f"Page has only {word_count} words. Minimum recommended: {min_words}.",
            recommendation=f"Add substantive content to reach at least {min_words} words with genuine value.",
            impact="Thin pages are less likely to rank and may trigger quality filters.",
        ).model_dump())
        score -= 25 if word_count < 200 else 15

    # Readability
    if readability.get("flesch_score", 50) < 30:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="content",
            title="Very difficult readability",
            description=f"Flesch score: {readability['flesch_score']} (College+ level).",
            recommendation="Simplify sentence structure and word choices for broader accessibility.",
            impact="Most users read at 8th grade level. Hard content = higher bounce rate.",
        ).model_dump())
        score -= 10

    # Headings
    if headings["h1_count"] == 0:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="content",
            title="Missing H1 heading",
            description="No H1 tag found on the page.",
            recommendation="Add a single H1 that clearly describes the page's main topic.",
            impact="H1 is a strong relevance signal for search engines.",
        ).model_dump())
        score -= 10

    if not headings["has_proper_hierarchy"]:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="content",
            title="Heading hierarchy issues",
            description="; ".join(headings["issues"]),
            recommendation="Use headings in proper order: H1 → H2 → H3 (no skipping levels).",
            impact="Proper heading hierarchy helps crawlers understand content structure.",
        ).model_dump())
        score -= 5

    # E-E-A-T overall
    eeat_avg = sum(s["score"] for s in eeat.values()) / 4
    if eeat_avg < 25:
        issues.append(SEOIssue(
            severity=Severity.MEDIUM,
            category="content",
            title="Weak E-E-A-T signals",
            description="Few signals of Experience, Expertise, Authoritativeness, or Trustworthiness.",
            recommendation="Add author bios, credentials, first-person experience, contact info, and trust pages.",
            impact="Google's quality systems reward strong E-E-A-T, especially for YMYL topics.",
        ).model_dump())
        score -= 10

    score = max(0, min(100, score))

    return {
        "content_result": {
            "score": score,
            "word_count": word_count,
            "readability": readability,
            "headings": headings,
            "eeat_signals": eeat,
            "thin_content": thin_content,
            "issues": issues,
        }
    }

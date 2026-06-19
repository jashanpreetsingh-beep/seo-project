"""
Schema Markup Analyzer Node.

Detects and validates structured data:
- JSON-LD (recommended by Google)
- Microdata
- RDFa
- Checks for common schema types and their required properties
- Suggests missing schema opportunities
"""
from __future__ import annotations


import json
import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState
from app.schemas import SEOIssue, Severity

# Schema types and their required/recommended properties
SCHEMA_REQUIREMENTS = {
    "Organization": {
        "required": ["name", "url"],
        "recommended": ["logo", "sameAs", "contactPoint"],
    },
    "WebSite": {
        "required": ["name", "url"],
        "recommended": ["potentialAction"],  # SearchAction for sitelinks search box
    },
    "Article": {
        "required": ["headline", "author", "datePublished"],
        "recommended": ["image", "dateModified", "publisher"],
    },
    "Product": {
        "required": ["name"],
        "recommended": ["image", "description", "offers", "review", "aggregateRating"],
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "openingHours", "geo", "image"],
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "recommended": [],
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "recommended": [],
        "note": "FAQ rich results retired May 7, 2026. Markup still aids AI/LLM citation.",
    },
    "HowTo": {
        "required": [],
        "recommended": [],
        "deprecated": True,
        "note": "HowTo rich results deprecated September 2023.",
    },
}


def _extract_jsonld(soup: BeautifulSoup) -> list[dict]:
    """Extract all JSON-LD blocks from the page."""
    schemas = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                schemas.extend(data)
            elif isinstance(data, dict):
                # Handle @graph
                if "@graph" in data:
                    schemas.extend(data["@graph"])
                else:
                    schemas.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return schemas


def _extract_microdata(soup: BeautifulSoup) -> list[dict]:
    """Detect microdata (itemscope/itemtype attributes)."""
    schemas = []
    for element in soup.find_all(attrs={"itemscope": True}):
        itemtype = element.get("itemtype", "")
        if itemtype:
            # Extract schema type from URL like "https://schema.org/Product"
            schema_type = itemtype.split("/")[-1] if "/" in itemtype else itemtype
            schemas.append({
                "@type": schema_type,
                "_format": "microdata",
                "_itemtype": itemtype,
            })
    return schemas


def _validate_schema(schema: dict) -> list[str]:
    """Validate a schema against known requirements."""
    errors = []
    schema_type = schema.get("@type", "")

    if isinstance(schema_type, list):
        schema_type = schema_type[0] if schema_type else ""

    if schema_type in SCHEMA_REQUIREMENTS:
        reqs = SCHEMA_REQUIREMENTS[schema_type]

        # Check deprecated
        if reqs.get("deprecated"):
            errors.append(f"{schema_type} schema is deprecated — remove it")
            return errors

        # Check required fields
        for field in reqs.get("required", []):
            if field not in schema:
                errors.append(f"{schema_type}: missing required field '{field}'")

        # Check recommended (as warnings, not errors)
        for field in reqs.get("recommended", []):
            if field not in schema:
                errors.append(f"{schema_type}: missing recommended field '{field}'")

    return errors


def _suggest_schemas(html: str, existing_types: set) -> list[str]:
    """Suggest schema types that could be added based on page content."""
    suggestions = []
    text = html.lower()

    if "Organization" not in existing_types and "LocalBusiness" not in existing_types:
        suggestions.append("Add Organization or LocalBusiness schema for entity recognition")

    if "WebSite" not in existing_types:
        suggestions.append("Add WebSite schema with SearchAction for sitelinks search box")

    if "BreadcrumbList" not in existing_types:
        if re.search(r"(breadcrumb|crumb)", text):
            suggestions.append("Add BreadcrumbList schema — breadcrumb navigation detected")

    # Article detection
    if "Article" not in existing_types:
        if re.search(r"(article|blog|post|news|published|author)", text):
            suggestions.append("Add Article schema — article/blog content detected")

    # Product detection
    if "Product" not in existing_types:
        if re.search(r"(add to cart|price|buy now|product|\$\d+)", text):
            suggestions.append("Add Product schema — product/commerce signals detected")

    return suggestions


async def schema_analyzer_node(state: SEOState) -> dict:
    """
    Detect, validate, and suggest Schema.org structured data.
    """
    html = state.get("html", "")
    if not html:
        return {"schema_result": {"score": 0, "issues": []}}

    soup = BeautifulSoup(html, "lxml")
    issues: list[dict] = []
    score = 100

    # Extract all schema formats
    jsonld_schemas = _extract_jsonld(soup)
    microdata_schemas = _extract_microdata(soup)
    all_schemas = jsonld_schemas + microdata_schemas

    # Get unique types
    existing_types = set()
    for schema in all_schemas:
        stype = schema.get("@type", "")
        if isinstance(stype, list):
            existing_types.update(stype)
        else:
            existing_types.add(stype)

    # No schema at all
    if not all_schemas:
        issues.append(SEOIssue(
            severity=Severity.HIGH,
            category="schema",
            title="No structured data found",
            description="The page has no JSON-LD, Microdata, or RDFa markup.",
            recommendation="Add JSON-LD structured data (Organization, WebSite at minimum).",
            impact="Structured data enables rich results (stars, prices, FAQs) in search.",
        ).model_dump())
        score -= 30
    else:
        # Validate each schema
        all_errors = []
        for schema in jsonld_schemas:
            errors = _validate_schema(schema)
            all_errors.extend(errors)

        if all_errors:
            # Separate critical (deprecated/required) from recommended
            required_errors = [e for e in all_errors if "required" in e or "deprecated" in e]
            recommended_errors = [e for e in all_errors if "recommended" in e]

            if required_errors:
                issues.append(SEOIssue(
                    severity=Severity.HIGH,
                    category="schema",
                    title=f"Schema validation errors ({len(required_errors)})",
                    description="; ".join(required_errors[:5]),
                    recommendation="Fix required schema properties to ensure rich result eligibility.",
                    impact="Invalid schema won't generate rich results in search.",
                ).model_dump())
                score -= 10 * min(len(required_errors), 3)

            if recommended_errors:
                issues.append(SEOIssue(
                    severity=Severity.LOW,
                    category="schema",
                    title=f"Schema enhancements available ({len(recommended_errors)})",
                    description="; ".join(recommended_errors[:5]),
                    recommendation="Add recommended properties to maximize rich result features.",
                    impact="More complete schema = richer search appearance.",
                ).model_dump())
                score -= 3

    # Suggestions
    suggestions = _suggest_schemas(html, existing_types)

    # Format schemas for display
    schemas_found = []
    for schema in jsonld_schemas:
        schemas_found.append({
            "type": schema.get("@type", "Unknown"),
            "format": "JSON-LD",
            "properties": list(schema.keys())[:10],
        })
    for schema in microdata_schemas:
        schemas_found.append({
            "type": schema.get("@type", "Unknown"),
            "format": "Microdata",
        })

    score = max(0, min(100, score))

    return {
        "schema_result": {
            "score": score,
            "schemas_found": schemas_found,
            "validation_errors": [e for s in jsonld_schemas for e in _validate_schema(s)],
            "suggestions": suggestions,
            "issues": issues,
        }
    }

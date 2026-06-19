"""
Store Content Node - Saves page content as embeddings in ChromaDB.

This node runs AFTER the content analyzer (which extracts text) and stores
the page's text content as vector embeddings for:
- Semantic search across all audited pages
- Content comparison between audits
- Knowledge base building over time

Uses sentence-transformers for local embeddings (no API calls).
Uses ChromaDB for persistent vector storage.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.graph.state import SEOState


def _extract_clean_text(html: str) -> str:
    """Extract clean visible text from HTML for embedding storage."""
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def store_content_node(state: SEOState) -> dict:
    """
    Extract page text and store as embeddings in ChromaDB.

    This runs after analyzers have completed so we can include
    metadata like health_score and site_type in the stored documents.

    Returns empty dict (doesn't modify state — purely a side effect node).
    """
    html = state.get("html", "")
    url = state.get("url", "")

    if not html or state.get("fetch_error"):
        return {}

    try:
        from app.vectorstore import store_page_content

        # Extract clean text
        text = _extract_clean_text(html)

        if not text:
            return {}

        # Gather metadata from the audit results
        metadata = {
            "site_type": state.get("site_type", "other"),
            "health_score": state.get("health_score", 0),
            "status_code": state.get("status_code", 200),
            "word_count": state.get("content_result", {}).get("word_count", 0) if state.get("content_result") else 0,
        }

        # Store in ChromaDB
        result = store_page_content(url=url, text=text, metadata=metadata)
        print(f"📦 Stored content for {url}: {result['chunks_stored']} chunks ({result['status']})")

    except ImportError as e:
        print(f"⚠️  Vector store not available (missing dependency): {e}")
    except Exception as e:
        # Non-fatal — don't break the audit if storage fails
        print(f"⚠️  Content storage failed (non-fatal): {e}")

    return {}

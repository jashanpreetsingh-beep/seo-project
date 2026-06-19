"""
Competitive Content Gap Analysis Pipeline.

Flow:
    User Query
         ↓
    Embedding (sentence-transformers, local)
         ↓
    Search My Site (ChromaDB - stored embeddings)
         ↓
    Search Competitors (live fetch → chunk → embed → compare)
         ↓
    Rerank Results (cross-encoder reranking for precision)
         ↓
    Generate Comparison (side-by-side content analysis)
         ↓
    Gap Detection (what competitors cover that you don't)
         ↓
    Recommendations (actionable content improvements)

All embeddings are local (sentence-transformers). 
LLM calls (Groq/Anthropic) only for the final recommendation step.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.vectorstore import (
    get_embedding_model,
    get_collection,
    chunk_text,
    search_content,
)


# ─── Step 1: Embed the user query ────────────────────────────────────────────


def embed_query(query: str) -> list[float]:
    """Generate embedding for the user's search query."""
    model = get_embedding_model()
    return model.encode([query], show_progress_bar=False).tolist()[0]


# ─── Step 2: Search my site (from stored embeddings) ─────────────────────────


def search_my_site(query: str, my_url: Optional[str] = None, n_results: int = 10) -> list[dict]:
    """
    Search stored embeddings for content from my site.
    
    If my_url is provided, filters to that domain only.
    Otherwise searches all stored content.
    """
    results = search_content(query=query, n_results=n_results, url_filter=my_url)
    
    # If filtering by domain (not exact URL), filter manually
    if my_url and "://" in my_url:
        my_domain = urlparse(my_url).netloc
        results = [
            r for r in results
            if my_domain in r.get("metadata", {}).get("url", "")
        ]
    
    return results


async def search_my_site_with_fallback(
    query: str, my_url: str, n_results: int = 10
) -> list[dict]:
    """
    Search stored embeddings first. If nothing is found, fetch the page live
    (same as competitors) so the analysis can still proceed without a prior audit.
    """
    results = search_my_site(query=query, my_url=my_url, n_results=n_results)
    
    if results:
        return results
    
    # Fallback: fetch live and treat like a competitor page
    print(f"⚠️  No stored embeddings for {my_url} — fetching live for comparison")
    results = await search_competitor(query=query, competitor_url=my_url, n_results=n_results)
    
    # Tag results as my_site so downstream logic knows the source
    for r in results:
        if r.get("metadata"):
            r["metadata"]["source"] = "my_site"
    
    return results


# ─── Step 3: Fetch & search competitor content (live) ─────────────────────────


async def fetch_page_text(url: str) -> str:
    """Fetch a URL and extract clean text content."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.FETCH_TIMEOUT,
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "aside", "noscript"]):
                tag.decompose()
            
            text = soup.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
    except Exception as e:
        return ""


async def search_competitor(query: str, competitor_url: str, n_results: int = 10) -> list[dict]:
    """
    Fetch competitor page, chunk it, embed it, and find relevant chunks.
    
    This does NOT store competitor content permanently — it's an in-memory
    comparison only. Competitor data is ephemeral.
    """
    model = get_embedding_model()
    
    # Fetch competitor content
    text = await fetch_page_text(competitor_url)
    if not text:
        return []
    
    # Chunk the competitor content
    chunks = chunk_text(text)
    if not chunks:
        return []
    
    # Embed all chunks
    chunk_embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    
    # Embed the query
    query_embedding = model.encode([query], show_progress_bar=False).tolist()[0]
    
    # Calculate similarities (cosine similarity via dot product since vectors are normalized)
    import numpy as np
    query_vec = np.array(query_embedding)
    chunk_vecs = np.array(chunk_embeddings)
    
    # Normalize for cosine similarity
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    chunk_norms = chunk_vecs / (np.linalg.norm(chunk_vecs, axis=1, keepdims=True) + 1e-10)
    
    similarities = chunk_norms @ query_norm
    
    # Sort by similarity and take top N
    top_indices = np.argsort(similarities)[::-1][:n_results]
    
    results = []
    for idx in top_indices:
        results.append({
            "content": chunks[idx],
            "similarity": float(similarities[idx]),
            "metadata": {
                "url": competitor_url,
                "chunk_index": str(idx),
                "chunk_total": str(len(chunks)),
                "source": "competitor",
            },
        })
    
    return results


# ─── Step 4: Rerank results ──────────────────────────────────────────────────


def rerank_results(
    query: str,
    my_results: list[dict],
    competitor_results: list[dict],
    top_k: int = 10,
) -> list[dict]:
    """
    Rerank combined results using cross-encoder for better precision.
    
    Falls back to similarity score ranking if cross-encoder not available.
    """
    # Combine all results with source tags
    all_results = []
    for r in my_results:
        r["source"] = "my_site"
        all_results.append(r)
    for r in competitor_results:
        r["source"] = "competitor"
        all_results.append(r)
    
    # Try cross-encoder reranking (more accurate than bi-encoder similarity)
    try:
        from sentence_transformers import CrossEncoder
        
        cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        pairs = [(query, r["content"]) for r in all_results]
        scores = cross_encoder.predict(pairs)
        
        for i, score in enumerate(scores):
            all_results[i]["rerank_score"] = float(score)
        
        # Sort by rerank score
        all_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
    except (ImportError, Exception):
        # Fallback: sort by original similarity
        all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    
    return all_results[:top_k]


# ─── Step 5: Generate comparison ─────────────────────────────────────────────


def generate_comparison(
    query: str,
    my_results: list[dict],
    competitor_results: list[dict],
) -> dict:
    """
    Generate a side-by-side content comparison.
    
    Purely algorithmic — no LLM needed for this step.
    """
    model = get_embedding_model()
    
    # Extract key topics from each side
    my_text = " ".join([r["content"] for r in my_results])
    competitor_text = " ".join([r["content"] for r in competitor_results])
    
    my_word_count = len(my_text.split())
    competitor_word_count = len(competitor_text.split())
    
    # Calculate content overlap using embeddings
    if my_text and competitor_text:
        embeddings = model.encode([my_text[:2000], competitor_text[:2000]], show_progress_bar=False)
        import numpy as np
        similarity = float(np.dot(embeddings[0], embeddings[1]) / (
            np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]) + 1e-10
        ))
    else:
        similarity = 0.0
    
    return {
        "query": query,
        "my_site": {
            "chunks_found": len(my_results),
            "total_words": my_word_count,
            "avg_similarity": sum(r.get("similarity", 0) for r in my_results) / max(len(my_results), 1),
            "top_content_preview": my_results[0]["content"][:300] if my_results else "",
        },
        "competitor": {
            "chunks_found": len(competitor_results),
            "total_words": competitor_word_count,
            "avg_similarity": sum(r.get("similarity", 0) for r in competitor_results) / max(len(competitor_results), 1),
            "top_content_preview": competitor_results[0]["content"][:300] if competitor_results else "",
        },
        "content_overlap": round(similarity, 4),
        "depth_difference": competitor_word_count - my_word_count,
    }


# ─── Step 6: Gap detection ───────────────────────────────────────────────────


def detect_gaps(
    query: str,
    my_results: list[dict],
    competitor_results: list[dict],
) -> list[dict]:
    """
    Detect content gaps — topics competitors cover that my site doesn't.
    
    Uses embedding similarity to find competitor chunks that are
    semantically distant from all my site's content.
    """
    if not competitor_results or not my_results:
        return []
    
    model = get_embedding_model()
    import numpy as np
    
    # Embed my content chunks
    my_texts = [r["content"] for r in my_results]
    my_embeddings = model.encode(my_texts, show_progress_bar=False)
    
    gaps = []
    
    for comp_result in competitor_results:
        comp_text = comp_result["content"]
        comp_embedding = model.encode([comp_text], show_progress_bar=False)[0]
        
        # Calculate max similarity to any of my chunks
        similarities = []
        for my_emb in my_embeddings:
            sim = float(np.dot(comp_embedding, my_emb) / (
                np.linalg.norm(comp_embedding) * np.linalg.norm(my_emb) + 1e-10
            ))
            similarities.append(sim)
        
        max_similarity_to_my_content = max(similarities) if similarities else 0
        
        # If competitor content is NOT similar to my content → it's a gap
        if max_similarity_to_my_content < 0.6:  # Threshold: below 0.6 = gap
            gaps.append({
                "content": comp_text[:500],
                "gap_score": round(1 - max_similarity_to_my_content, 4),  # Higher = bigger gap
                "closest_my_similarity": round(max_similarity_to_my_content, 4),
                "competitor_url": comp_result.get("metadata", {}).get("url", ""),
                "topic_hint": _extract_topic_hint(comp_text),
            })
    
    # Sort by gap_score (biggest gaps first)
    gaps.sort(key=lambda x: x["gap_score"], reverse=True)
    
    return gaps[:10]  # Top 10 gaps


def _extract_topic_hint(text: str) -> str:
    """Extract a short topic hint from a text chunk (first sentence or 100 chars)."""
    sentences = re.split(r'[.!?]+', text.strip())
    if sentences:
        hint = sentences[0].strip()[:100]
        return hint
    return text[:100]


# ─── Step 7: LLM-powered recommendations ─────────────────────────────────────


async def generate_recommendations(
    query: str,
    comparison: dict,
    gaps: list[dict],
) -> list[dict]:
    """
    Use LLM (Groq or Anthropic) to generate actionable recommendations
    based on the gap analysis.
    
    This is the ONLY step that uses an LLM. Everything before is local embeddings.
    """
    if not gaps and not comparison:
        return []
    
    # Build prompt
    gaps_text = "\n".join(
        f"- GAP (score {g['gap_score']}): {g['topic_hint']}"
        for g in gaps[:7]
    )
    
    prompt = f"""Based on this competitive content gap analysis, provide 5-7 actionable content recommendations.

QUERY ANALYZED: "{query}"

MY SITE:
- Relevant chunks found: {comparison.get('my_site', {}).get('chunks_found', 0)}
- Total relevant words: {comparison.get('my_site', {}).get('total_words', 0)}
- Avg relevance score: {comparison.get('my_site', {}).get('avg_similarity', 0):.3f}

COMPETITOR:
- Relevant chunks found: {comparison.get('competitor', {}).get('chunks_found', 0)}
- Total relevant words: {comparison.get('competitor', {}).get('total_words', 0)}
- Avg relevance score: {comparison.get('competitor', {}).get('avg_similarity', 0):.3f}

CONTENT OVERLAP: {comparison.get('content_overlap', 0):.1%}
DEPTH DIFFERENCE: Competitor has {abs(comparison.get('depth_difference', 0))} {'more' if comparison.get('depth_difference', 0) > 0 else 'fewer'} words

CONTENT GAPS (topics competitor covers that my site doesn't):
{gaps_text}

Return a JSON array with recommendations:
[
  {{
    "priority": 1,
    "action": "specific content action",
    "gap_addressed": "which gap this fixes",
    "estimated_words_needed": 500,
    "impact": "high/medium/low",
    "rationale": "why this matters for SEO"
  }}
]

Return ONLY valid JSON. No markdown, no code blocks."""

    try:
        llm = _get_llm()
        if not llm:
            return _fallback_recommendations(gaps, comparison)
        
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="You are an SEO content strategist. Return only valid JSON."),
            HumanMessage(content=prompt),
        ]
        
        response = await llm.ainvoke(messages)
        
        import json
        recommendations = json.loads(response.content)
        if isinstance(recommendations, list):
            return recommendations
    except Exception as e:
        print(f"LLM recommendations failed: {e}")
    
    return _fallback_recommendations(gaps, comparison)


def _get_llm():
    """Get the configured LLM (Groq or Anthropic)."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "groq" and settings.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY,
                temperature=0.3,
                max_tokens=2000,
            )
        except ImportError:
            pass
    
    if settings.ANTHROPIC_API_KEY:
        try:
            from langchain_anthropic import ChatAnthropic
            kwargs = {
                "model": settings.ANTHROPIC_MODEL,
                "anthropic_api_key": settings.ANTHROPIC_API_KEY,
                "max_tokens": 2000,
                "temperature": 0.3,
            }
            if settings.ANTHROPIC_BASE_URL:
                kwargs["anthropic_api_url"] = settings.ANTHROPIC_BASE_URL
            return ChatAnthropic(**kwargs)
        except ImportError:
            pass
    
    return None


def _fallback_recommendations(gaps: list[dict], comparison: dict) -> list[dict]:
    """Generate rule-based recommendations when LLM is not available."""
    recommendations = []
    
    for i, gap in enumerate(gaps[:5], 1):
        recommendations.append({
            "priority": i,
            "action": f"Create content covering: {gap['topic_hint']}",
            "gap_addressed": gap["topic_hint"],
            "estimated_words_needed": 800,
            "impact": "high" if gap["gap_score"] > 0.6 else "medium",
            "rationale": f"Competitor covers this topic (gap score: {gap['gap_score']}) but your site doesn't.",
        })
    
    if comparison.get("depth_difference", 0) > 500:
        recommendations.append({
            "priority": len(recommendations) + 1,
            "action": "Expand existing content depth",
            "gap_addressed": "Overall content depth",
            "estimated_words_needed": comparison["depth_difference"],
            "impact": "medium",
            "rationale": f"Competitor has {comparison['depth_difference']} more words of relevant content.",
        })
    
    return recommendations


# ─── Main pipeline orchestrator ───────────────────────────────────────────────


async def run_competitive_gap_analysis(
    query: str,
    my_url: str,
    competitor_urls: list[str],
    n_results: int = 10,
) -> dict:
    """
    Run the full competitive content gap analysis pipeline.
    
    Args:
        query: The topic/keyword to analyze
        my_url: Your site URL (must have been previously audited)
        competitor_urls: List of competitor page URLs to compare against
        n_results: Number of chunks to retrieve per source
        
    Returns:
        Complete analysis with comparison, gaps, and recommendations
    """
    # Step 1 & 2: Search my site's stored embeddings (with live fallback)
    my_results = await search_my_site_with_fallback(query=query, my_url=my_url, n_results=n_results)
    
    # Step 3: Fetch and search competitor content (live)
    all_competitor_results = []
    competitor_details = {}
    
    for comp_url in competitor_urls:
        comp_results = await search_competitor(
            query=query,
            competitor_url=comp_url,
            n_results=n_results,
        )
        all_competitor_results.extend(comp_results)
        competitor_details[comp_url] = {
            "chunks_found": len(comp_results),
            "avg_similarity": sum(r.get("similarity", 0) for r in comp_results) / max(len(comp_results), 1),
        }
    
    # Step 4: Rerank combined results
    reranked = rerank_results(
        query=query,
        my_results=my_results,
        competitor_results=all_competitor_results,
        top_k=n_results * 2,
    )
    
    # Step 5: Generate comparison
    comparison = generate_comparison(
        query=query,
        my_results=my_results,
        competitor_results=all_competitor_results,
    )
    
    # Step 6: Detect gaps
    gaps = detect_gaps(
        query=query,
        my_results=my_results,
        competitor_results=all_competitor_results,
    )
    
    # Step 7: Generate recommendations (LLM-powered)
    recommendations = await generate_recommendations(
        query=query,
        comparison=comparison,
        gaps=gaps,
    )
    
    return {
        "query": query,
        "my_url": my_url,
        "competitor_urls": competitor_urls,
        "comparison": comparison,
        "gaps": gaps,
        "reranked_results": reranked[:5],  # Top 5 for response brevity
        "competitor_details": competitor_details,
        "recommendations": recommendations,
        "summary": {
            "total_gaps_found": len(gaps),
            "content_overlap": comparison.get("content_overlap", 0),
            "my_relevance": comparison.get("my_site", {}).get("avg_similarity", 0),
            "competitor_relevance": comparison.get("competitor", {}).get("avg_similarity", 0),
            "depth_gap": comparison.get("depth_difference", 0),
        },
    }

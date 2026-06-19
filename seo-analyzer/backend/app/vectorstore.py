"""
Vector Store - ChromaDB + Sentence-Transformers integration.

Stores page content as embeddings so that:
- Previously audited content is searchable by semantic similarity
- We can detect content changes between audits
- Users can query across all audited pages (e.g., "find pages about pricing")

Uses:
- ChromaDB: lightweight vector database (persisted to disk)
- sentence-transformers: local embedding model (no API calls needed)
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import settings

# ─── Singleton instances ──────────────────────────────────────────────────────

_chroma_client: Optional[chromadb.ClientAPI] = None
_embedding_model: Optional[SentenceTransformer] = None

COLLECTION_NAME = "seo_page_content"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast, 384-dim, good quality
CHUNK_SIZE = 500  # words per chunk
CHUNK_OVERLAP = 50  # word overlap between chunks


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_embedding_model() -> SentenceTransformer:
    """Get or load the sentence-transformers model (cached after first load)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_collection() -> chromadb.Collection:
    """Get or create the page content collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "SEO page content chunks with embeddings"},
    )


# ─── Content chunking ────────────────────────────────────────────────────────


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    Args:
        text: The text to split
        chunk_size: Number of words per chunk
        overlap: Number of overlapping words between chunks

    Returns:
        List of text chunks
    """
    words = text.split()
    if len(words) <= chunk_size:
        return [text] if words else []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def _generate_chunk_id(url: str, chunk_index: int) -> str:
    """Generate a deterministic ID for a URL chunk."""
    raw = f"{url}::chunk::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ─── Store content ───────────────────────────────────────────────────────────


def store_page_content(url: str, text: str, metadata: Optional[dict] = None) -> dict:
    """
    Store page content as embeddings in ChromaDB.

    Steps:
    1. Chunk the text into manageable pieces
    2. Generate embeddings using sentence-transformers
    3. Upsert into ChromaDB with metadata

    Args:
        url: The page URL (used as document identifier)
        text: Extracted text content from the page
        metadata: Optional extra metadata (site_type, health_score, etc.)

    Returns:
        Dict with storage stats (chunks_stored, collection_size)
    """
    if not text or not text.strip():
        return {"chunks_stored": 0, "collection_size": 0, "status": "skipped_empty"}

    collection = get_collection()
    model = get_embedding_model()

    # Chunk the content
    chunks = chunk_text(text)
    if not chunks:
        return {"chunks_stored": 0, "collection_size": 0, "status": "skipped_no_chunks"}

    # Generate embeddings
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()

    # Prepare data for ChromaDB
    ids = [_generate_chunk_id(url, i) for i in range(len(chunks))]
    now = datetime.now(timezone.utc).isoformat()

    base_metadata = {
        "url": url,
        "stored_at": now,
    }
    if metadata:
        base_metadata.update({k: str(v) for k, v in metadata.items() if v is not None})

    metadatas = [
        {**base_metadata, "chunk_index": str(i), "chunk_total": str(len(chunks))}
        for i in range(len(chunks))
    ]

    # Delete existing entries for this URL (so re-audits update the content)
    try:
        existing = collection.get(where={"url": url})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # Collection might be empty or filter not supported yet

    # Upsert chunks with embeddings
    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return {
        "chunks_stored": len(chunks),
        "collection_size": collection.count(),
        "status": "stored",
    }


# ─── Search content ─────────────────────────────────────────────────────────


def search_content(query: str, n_results: int = 5, url_filter: Optional[str] = None) -> list[dict]:
    """
    Semantic search across all stored page content.

    Args:
        query: Natural language search query
        n_results: Number of results to return
        url_filter: Optional URL to restrict search to a specific page

    Returns:
        List of matching chunks with metadata and similarity scores
    """
    collection = get_collection()
    model = get_embedding_model()

    if collection.count() == 0:
        return []

    # Generate query embedding
    query_embedding = model.encode([query], show_progress_bar=False).tolist()

    # Build query kwargs
    query_kwargs = {
        "query_embeddings": query_embedding,
        "n_results": min(n_results, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }

    if url_filter:
        query_kwargs["where"] = {"url": url_filter}

    results = collection.query(**query_kwargs)

    # Format results
    formatted = []
    for i in range(len(results["ids"][0])):
        formatted.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
            "similarity": 1 - results["distances"][0][i],  # Convert distance to similarity
        })

    return formatted

"""
Search API Routes — Semantic search across stored page content.

POST /api/search         — Search across all audited page content using natural language
GET  /api/search/stats   — Get vector store statistics
GET  /api/search/embeddings — List all stored embeddings with metadata
GET  /api/search/embeddings/{url} — Get embeddings for a specific URL
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    """Request body for semantic search."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    url_filter: Optional[str] = Field(default=None, description="Restrict search to a specific URL")


class SearchResult(BaseModel):
    """A single search result."""
    content: str
    url: str
    similarity: float
    chunk_index: str
    stored_at: str
    site_type: Optional[str] = None
    health_score: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response with results."""
    query: str
    results: list[SearchResult]
    total_results: int


@router.post("", response_model=SearchResponse)
async def search_content(request: SearchRequest):
    """
    Semantic search across all previously audited page content.

    This searches the ChromaDB vector store using sentence-transformers embeddings.
    Returns the most relevant content chunks matching the query.
    """
    try:
        from app.vectorstore import search_content as do_search
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vector store not available (missing dependency): {e}",
        )

    try:
        raw_results = do_search(
            query=request.query,
            n_results=request.n_results,
            url_filter=request.url_filter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    results = []
    for r in raw_results:
        meta = r.get("metadata", {})
        results.append(SearchResult(
            content=r["content"],
            url=meta.get("url", ""),
            similarity=round(r["similarity"], 4),
            chunk_index=meta.get("chunk_index", "0"),
            stored_at=meta.get("stored_at", ""),
            site_type=meta.get("site_type"),
            health_score=meta.get("health_score"),
        ))

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results),
    )


# ─── Embeddings Inspection Endpoints ─────────────────────────────────────────


class EmbeddingInfo(BaseModel):
    """Info about a stored embedding chunk."""
    id: str
    content_preview: str  # First 200 chars of the chunk
    url: str
    chunk_index: str
    chunk_total: str
    stored_at: str
    site_type: Optional[str] = None
    health_score: Optional[str] = None
    embedding_dimensions: int
    embedding_sample: list[float]  # First 5 values of the embedding vector


class StatsResponse(BaseModel):
    """Vector store statistics."""
    total_chunks: int
    unique_urls: list[str]
    collection_name: str
    embedding_model: str
    embedding_dimensions: int


class EmbeddingsListResponse(BaseModel):
    """List of stored embeddings."""
    total: int
    embeddings: list[EmbeddingInfo]


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get vector store statistics — total chunks stored, unique URLs, model info.
    """
    try:
        from app.vectorstore import get_collection, COLLECTION_NAME, EMBEDDING_MODEL_NAME
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Vector store not available: {e}")

    try:
        collection = get_collection()
        total = collection.count()

        # Get all unique URLs
        unique_urls = []
        if total > 0:
            all_data = collection.get(include=["metadatas"])
            urls_seen = set()
            for meta in all_data.get("metadatas", []):
                url = meta.get("url", "")
                if url and url not in urls_seen:
                    urls_seen.add(url)
                    unique_urls.append(url)

        return StatsResponse(
            total_chunks=total,
            unique_urls=sorted(unique_urls),
            collection_name=COLLECTION_NAME,
            embedding_model=EMBEDDING_MODEL_NAME,
            embedding_dimensions=384,  # all-MiniLM-L6-v2 produces 384-dim vectors
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/embeddings", response_model=EmbeddingsListResponse)
async def list_embeddings(
    url: Optional[str] = Query(default=None, description="Filter by URL"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """
    List all stored embeddings with their metadata and a sample of the vector.

    Use this to verify content is being stored correctly after an audit.
    """
    try:
        from app.vectorstore import get_collection
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Vector store not available: {e}")

    try:
        collection = get_collection()
        total = collection.count()

        if total == 0:
            return EmbeddingsListResponse(total=0, embeddings=[])

        # Fetch data from ChromaDB
        if url:
            data = collection.get(
                where={"url": url},
                include=["documents", "metadatas", "embeddings"],
            )
        else:
            data = collection.get(
                include=["documents", "metadatas", "embeddings"],
            )

        embeddings_list = []
        ids = data.get("ids", [])
        docs = data.get("documents", [])
        metas = data.get("metadatas", [])
        embeds = data.get("embeddings", [])

        # Apply pagination
        start = min(offset, len(ids))
        end = min(start + limit, len(ids))

        for i in range(start, end):
            embedding_vector = embeds[i] if embeds and i < len(embeds) else []
            meta = metas[i] if metas and i < len(metas) else {}
            doc = docs[i] if docs and i < len(docs) else ""

            embeddings_list.append(EmbeddingInfo(
                id=ids[i],
                content_preview=doc[:200] + ("..." if len(doc) > 200 else ""),
                url=meta.get("url", ""),
                chunk_index=meta.get("chunk_index", "0"),
                chunk_total=meta.get("chunk_total", "0"),
                stored_at=meta.get("stored_at", ""),
                site_type=meta.get("site_type"),
                health_score=meta.get("health_score"),
                embedding_dimensions=len(embedding_vector) if embedding_vector else 0,
                embedding_sample=embedding_vector[:5] if embedding_vector else [],
            ))

        return EmbeddingsListResponse(
            total=len(ids),
            embeddings=embeddings_list,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list embeddings: {str(e)}")

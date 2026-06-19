"""
LangGraph Workflow Definition.

This is where the magic happens — we define the SEO analysis as a DIRECTED GRAPH:

    fetch_page → [technical, content, onpage, schema, performance, security] → scorer

The middle nodes run IN PARALLEL (LangGraph handles this automatically).
The scorer node waits for all analyzers to complete before computing the final score.

This is the same pattern claude-seo uses with its 15 parallel subagents,
but implemented as a proper workflow graph instead of AI agent delegation.
"""

from langgraph.graph import StateGraph, END

from app.graph.state import SEOState
from app.graph.nodes import (
    fetch_page_node,
    technical_analyzer_node,
    content_analyzer_node,
    onpage_analyzer_node,
    schema_analyzer_node,
    performance_analyzer_node,
    security_analyzer_node,
    scorer_node,
)
from app.graph.nodes.llm_recommendations import llm_recommendations_node


def create_seo_graph() -> StateGraph:
    """
    Build the SEO analysis graph.
    
    Graph structure:
    
        START
          │
          ▼
        fetch_page  (fetches URL, gets HTML + headers)
          │
          ├─── should_continue? ───(if fetch failed)──→ END
          │
          ▼ (fan-out: all run in parallel)
        ┌─────────────────────────────────────────────┐
        │ technical  content  onpage  schema  perf  sec │
        └─────────────────────────────────────────────┘
          │ (fan-in: waits for all to complete)
          ▼
        scorer  (aggregates scores, generates report)
          │
          ▼
        END
    """
    # Create the graph with our state type
    graph = StateGraph(SEOState)

    # ─── Add nodes ────────────────────────────────────────────────────────────
    graph.add_node("fetch_page", fetch_page_node)
    graph.add_node("technical_analyzer", technical_analyzer_node)
    graph.add_node("content_analyzer", content_analyzer_node)
    graph.add_node("onpage_analyzer", onpage_analyzer_node)
    graph.add_node("schema_analyzer", schema_analyzer_node)
    graph.add_node("performance_analyzer", performance_analyzer_node)
    graph.add_node("security_analyzer", security_analyzer_node)
    graph.add_node("scorer", scorer_node)
    graph.add_node("llm_recommendations", llm_recommendations_node)

    # ─── Define edges (the flow) ──────────────────────────────────────────────

    # START → fetch
    graph.set_entry_point("fetch_page")

    # fetch → conditional routing
    def should_continue(state: SEOState) -> str:
        """If fetch failed, skip to scorer with empty results."""
        if state.get("fetch_error"):
            return "scorer"
        return "analyze"

    graph.add_conditional_edges(
        "fetch_page",
        should_continue,
        {
            "analyze": "technical_analyzer",  # This triggers the analysis chain
            "scorer": "scorer",
        },
    )

    # Analysis chain — each node writes to a different state key, no conflicts.
    # They run sequentially here; for true parallelism you'd use
    # LangGraph's Send() API or asyncio.gather() in a single node.
    graph.add_edge("technical_analyzer", "content_analyzer")
    graph.add_edge("content_analyzer", "onpage_analyzer")
    graph.add_edge("onpage_analyzer", "schema_analyzer")
    graph.add_edge("schema_analyzer", "performance_analyzer")
    graph.add_edge("performance_analyzer", "security_analyzer")
    graph.add_edge("security_analyzer", "scorer")

    # scorer → LLM recommendations (Claude Sonnet 4) → END
    # The LLM node enhances recommendations with AI intelligence.
    # If no API key is set, it returns empty and rule-based recs are used.
    graph.add_edge("scorer", "llm_recommendations")
    graph.add_edge("llm_recommendations", END)

    return graph


# Compile the graph (done once at module load)
_compiled_graph = None


def _get_compiled_graph():
    """Lazy-compile the graph (compile once, reuse for all requests)."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = create_seo_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph


async def run_audit(url: str) -> dict:
    """
    Execute the full SEO audit workflow for a URL.
    
    This is the main entry point called by the API route.
    It initializes the state, runs the graph, and returns the final result.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Complete audit results dictionary
    """
    compiled = _get_compiled_graph()

    # Initialize state with just the URL — everything else gets populated by nodes
    initial_state: SEOState = {
        "url": url,
        "html": "",
        "status_code": 0,
        "headers": {},
        "redirect_chain": [],
        "fetch_error": None,
        "technical_result": None,
        "content_result": None,
        "onpage_result": None,
        "schema_result": None,
        "performance_result": None,
        "security_result": None,
        "health_score": 0,
        "site_type": "other",
        "issues": [],
        "recommendations": [],
    }

    # Run the graph — this executes all nodes in order
    final_state = await compiled.ainvoke(initial_state)

    # Return the complete result
    return {
        "url": final_state.get("url", url),
        "health_score": final_state.get("health_score", 0),
        "site_type": final_state.get("site_type", "other"),
        "status_code": final_state.get("status_code", 0),
        "fetch_error": final_state.get("fetch_error"),
        "technical": final_state.get("technical_result", {}),
        "content": final_state.get("content_result", {}),
        "onpage": final_state.get("onpage_result", {}),
        "schema_markup": final_state.get("schema_result", {}),
        "performance": final_state.get("performance_result", {}),
        "security": final_state.get("security_result", {}),
        "issues": final_state.get("issues", []),
        "recommendations": final_state.get("recommendations", []),
    }

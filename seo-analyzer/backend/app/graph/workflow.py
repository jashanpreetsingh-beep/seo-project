"""
LangGraph Workflow Definition.

The system uses a DIRECTED GRAPH with two major analysis branches:

    fetch_page → [SEO Analyzers] → scorer → LLM recommendations
                                          ↘
               → [GEO Agents] → GEO scorer → GEO improvement → GEO report

Architecture:
    WEBSITE URL
         │
         ▼
    MASTER ORCHESTRATOR (fetch_page)
         │
    ─────┴─────────────────────────────────
    │           │           │              │
    ▼           ▼           ▼              ▼
  CRAWLER    CONTEXT     SEO AGENT     GEO AGENT
  (fetch)    (content)   (technical    (AI Search
              (schema)    onpage        Visibility)
              (security)  performance)
    │           │           │              │
    └───────────┴───────────┴──────────────┘
                     │
                     ▼
           INTELLIGENCE LAYER (scorer + geo_scorer)
                     │
                     ▼
        GEO SCORING + IMPROVEMENT AGENT
                     │
                     ▼
            ACTION PLAN AGENT (geo_report)
                     │
                     ▼
             FINAL GEO REPORT
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
from app.graph.nodes.store_content import store_content_node
from app.graph.nodes.geo import (
    entity_understanding_node,
    answer_extraction_node,
    authority_trust_node,
    citation_probability_node,
    conversational_search_node,
    geo_scorer_node,
    geo_improvement_node,
    geo_report_node,
)


def create_seo_graph() -> StateGraph:
    """
    Build the combined SEO + GEO analysis graph.
    
    Graph structure:
    
        START
          │
          ▼
        fetch_page  (fetches URL, gets HTML + headers)
          │
          ├─── should_continue? ───(if fetch failed)──→ scorer → END
          │
          ▼ (sequential analysis chain)
        ┌─────────────────────────────────────────────────────────────┐
        │ SEO: technical → content → onpage → schema → perf → security │
        └─────────────────────────────────────────────────────────────┘
          │
          ▼
        scorer (SEO health score)
          │
          ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │ GEO: entity → answer → authority → citation → conversational    │
        └─────────────────────────────────────────────────────────────────┘
          │
          ▼
        geo_scorer (weighted GEO score)
          │
          ▼
        geo_improvement (prioritized actions)
          │
          ▼
        geo_report (final GEO strategy)
          │
          ▼
        llm_recommendations (Claude AI enhancement)
          │
          ▼
        END
    """
    # Create the graph with our state type
    graph = StateGraph(SEOState)

    # ─── Add SEO nodes ────────────────────────────────────────────────────────
    graph.add_node("fetch_page", fetch_page_node)
    graph.add_node("technical_analyzer", technical_analyzer_node)
    graph.add_node("content_analyzer", content_analyzer_node)
    graph.add_node("onpage_analyzer", onpage_analyzer_node)
    graph.add_node("schema_analyzer", schema_analyzer_node)
    graph.add_node("performance_analyzer", performance_analyzer_node)
    graph.add_node("security_analyzer", security_analyzer_node)
    graph.add_node("scorer", scorer_node)

    # ─── Add GEO nodes ────────────────────────────────────────────────────────
    graph.add_node("geo_entity", entity_understanding_node)
    graph.add_node("geo_answer", answer_extraction_node)
    graph.add_node("geo_authority", authority_trust_node)
    graph.add_node("geo_citation", citation_probability_node)
    graph.add_node("geo_conversational", conversational_search_node)
    graph.add_node("geo_scorer", geo_scorer_node)
    graph.add_node("geo_improvement", geo_improvement_node)
    graph.add_node("geo_report", geo_report_node)

    # ─── Add LLM enhancement node ────────────────────────────────────────────
    graph.add_node("llm_recommendations", llm_recommendations_node)
    graph.add_node("store_content", store_content_node)

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
            "analyze": "technical_analyzer",
            "scorer": "scorer",
        },
    )

    # SEO Analysis chain
    graph.add_edge("technical_analyzer", "content_analyzer")
    graph.add_edge("content_analyzer", "onpage_analyzer")
    graph.add_edge("onpage_analyzer", "schema_analyzer")
    graph.add_edge("schema_analyzer", "performance_analyzer")
    graph.add_edge("performance_analyzer", "security_analyzer")
    graph.add_edge("security_analyzer", "scorer")

    # scorer → GEO analysis chain
    graph.add_edge("scorer", "geo_entity")
    graph.add_edge("geo_entity", "geo_answer")
    graph.add_edge("geo_answer", "geo_authority")
    graph.add_edge("geo_authority", "geo_citation")
    graph.add_edge("geo_citation", "geo_conversational")
    graph.add_edge("geo_conversational", "geo_scorer")
    graph.add_edge("geo_scorer", "geo_improvement")
    graph.add_edge("geo_improvement", "geo_report")

    # GEO report → LLM recommendations → store_content → END
    # The LLM node enhances recommendations with AI intelligence.
    # If no API key is set, it returns empty and rule-based recs are used.
    # The store_content node saves page content to ChromaDB for semantic search.
    graph.add_edge("geo_report", "llm_recommendations")
    graph.add_edge("llm_recommendations", "store_content")
    graph.add_edge("store_content", END)

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
    Execute the full SEO + GEO audit workflow for a URL.
    
    This is the main entry point called by the API route.
    It initializes the state, runs the graph, and returns the final result
    containing both SEO analysis and GEO (AI visibility) analysis.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Complete audit results dictionary with SEO + GEO data
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
        # SEO
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
        "token_usage": None,
        # GEO
        "geo_entity_result": None,
        "geo_answer_result": None,
        "geo_authority_result": None,
        "geo_citation_result": None,
        "geo_conversational_result": None,
        "geo_score": 0,
        "geo_scores": None,
        "geo_visibility": None,
        "geo_strengths": None,
        "geo_weaknesses": None,
        "geo_all_issues": None,
        "geo_priority_actions": None,
        "geo_potential_score": 0,
        "geo_total_potential_gain": 0,
        "geo_report": None,
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
        # SEO results
        "technical": final_state.get("technical_result", {}),
        "content": final_state.get("content_result", {}),
        "onpage": final_state.get("onpage_result", {}),
        "schema_markup": final_state.get("schema_result", {}),
        "performance": final_state.get("performance_result", {}),
        "security": final_state.get("security_result", {}),
        "issues": final_state.get("issues", []),
        "recommendations": final_state.get("recommendations", []),
        "token_usage": final_state.get("token_usage"),
        # GEO results
        "geo": final_state.get("geo_report", {}),
        "geo_score": final_state.get("geo_score", 0),
    }

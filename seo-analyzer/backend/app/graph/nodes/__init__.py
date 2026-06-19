"""
LangGraph Analyzer Nodes.

Each node is a function that:
1. Receives the shared SEOState
2. Performs its specific analysis
3. Returns a partial state update (only the keys it writes to)

Nodes run in parallel where they don't depend on each other's output.
"""

from app.graph.nodes.fetch import fetch_page_node
from app.graph.nodes.technical import technical_analyzer_node
from app.graph.nodes.content import content_analyzer_node
from app.graph.nodes.onpage import onpage_analyzer_node
from app.graph.nodes.schema_check import schema_analyzer_node
from app.graph.nodes.performance import performance_analyzer_node
from app.graph.nodes.security import security_analyzer_node
from app.graph.nodes.scorer import scorer_node

__all__ = [
    "fetch_page_node",
    "technical_analyzer_node",
    "content_analyzer_node",
    "onpage_analyzer_node",
    "schema_analyzer_node",
    "performance_analyzer_node",
    "security_analyzer_node",
    "scorer_node",
]

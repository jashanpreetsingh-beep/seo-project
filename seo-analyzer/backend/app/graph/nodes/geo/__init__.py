"""
GEO (Generative Engine Optimization) Agent Nodes.

GEO analyzes how well a website is optimized for AI-powered search engines
(ChatGPT, Perplexity, Google AI Overviews, Copilot, etc.)

The GEO system uses 5 specialized agents:
1. Entity Understanding Agent - Can AI identify what this business is?
2. Answer Extraction Agent - Can AI extract direct answers from content?
3. Authority & Trust Agent - Why should AI trust this source?
4. Citation Probability Agent - Would AI cite this as a source?
5. Conversational Search Agent - Does content match how users ask AI?

Plus:
6. GEO Scorer - Computes weighted GEO score
7. GEO Improvement Agent - Generates prioritized fixes
8. GEO Report Agent - Produces final GEO strategy report
"""

from app.graph.nodes.geo.entity_understanding import entity_understanding_node
from app.graph.nodes.geo.answer_extraction import answer_extraction_node
from app.graph.nodes.geo.authority_trust import authority_trust_node
from app.graph.nodes.geo.citation_probability import citation_probability_node
from app.graph.nodes.geo.conversational_search import conversational_search_node
from app.graph.nodes.geo.geo_scorer import geo_scorer_node
from app.graph.nodes.geo.geo_improvement import geo_improvement_node
from app.graph.nodes.geo.geo_report import geo_report_node

__all__ = [
    "entity_understanding_node",
    "answer_extraction_node",
    "authority_trust_node",
    "citation_probability_node",
    "conversational_search_node",
    "geo_scorer_node",
    "geo_improvement_node",
    "geo_report_node",
]

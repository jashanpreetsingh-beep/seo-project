/**
 * Competitive Analysis Page - Run content gap analysis against competitor URLs.
 * Displays side-by-side comparison, content gaps, and actionable recommendations.
 */

import { useState } from 'react'
import {
  Loader2, Globe, Plus, X, Search, BarChart3,
  TrendingUp, AlertTriangle, Lightbulb, ArrowRight,
  Target, Layers, FileText, ChevronDown, ChevronUp
} from 'lucide-react'
import { runCompetitiveGap } from '../api'

function ScoreBar({ label, value, max = 1, color = 'bg-navy' }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{typeof value === 'number' ? value.toFixed(3) : value}</span>
      </div>
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function GapCard({ gap, index }) {
  const [expanded, setExpanded] = useState(false)
  const severity = gap.gap_score >= 0.7 ? 'high' : gap.gap_score >= 0.4 ? 'medium' : 'low'
  const severityColors = {
    high: 'border-red-200 bg-red-50',
    medium: 'border-amber-200 bg-amber-50',
    low: 'border-blue-200 bg-blue-50',
  }
  const severityBadge = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-blue-100 text-blue-700',
  }

  return (
    <div className={`rounded-xl border p-4 ${severityColors[severity]}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1 min-w-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-800 text-white flex items-center justify-center text-xs font-bold">
            {index + 1}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 text-sm">{gap.topic_hint}</p>
            <div className="flex flex-wrap items-center gap-2 mt-1.5">
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${severityBadge[severity]}`}>
                Gap Score: {(gap.gap_score * 100).toFixed(0)}%
              </span>
              {gap.competitor_url && (
                <span className="text-xs text-gray-500 truncate max-w-[200px]">
                  from: {new URL(gap.competitor_url).hostname}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-gray-400 hover:text-gray-600 ml-2"
          aria-label={expanded ? 'Collapse gap details' : 'Expand gap details'}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>
      {expanded && (
        <div className="mt-3 pl-10 text-sm text-gray-700 bg-white/60 rounded-lg p-3">
          <p>{gap.content}</p>
        </div>
      )}
    </div>
  )
}

function RecommendationCard({ rec }) {
  const impactColors = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-blue-100 text-blue-700',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-navy to-blue-600 text-white flex items-center justify-center text-sm font-bold">
          {rec.priority}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900">{rec.action}</p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${impactColors[rec.impact] || 'bg-gray-100 text-gray-700'}`}>
              {rec.impact} impact
            </span>
            {rec.estimated_words_needed && (
              <span className="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700 font-medium">
                ~{rec.estimated_words_needed} words
              </span>
            )}
          </div>
          {rec.rationale && (
            <p className="text-sm text-gray-500 mt-2">{rec.rationale}</p>
          )}
          {rec.gap_addressed && (
            <p className="text-xs text-gray-400 mt-1">
              Addresses: {rec.gap_addressed}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default function CompetitiveAnalysis() {
  const [query, setQuery] = useState('')
  const [myUrl, setMyUrl] = useState('')
  const [competitorUrls, setCompetitorUrls] = useState([''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [results, setResults] = useState(null)
  const [activeTab, setActiveTab] = useState('overview')

  const addCompetitor = () => {
    if (competitorUrls.length < 5) {
      setCompetitorUrls([...competitorUrls, ''])
    }
  }

  const removeCompetitor = (index) => {
    if (competitorUrls.length > 1) {
      setCompetitorUrls(competitorUrls.filter((_, i) => i !== index))
    }
  }

  const updateCompetitor = (index, value) => {
    const updated = [...competitorUrls]
    updated[index] = value
    setCompetitorUrls(updated)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || !myUrl.trim() || !competitorUrls.some(u => u.trim())) return

    setLoading(true)
    setError('')
    setResults(null)

    try {
      const result = await runCompetitiveGap({
        query: query.trim(),
        my_url: myUrl.trim(),
        competitor_urls: competitorUrls.filter(u => u.trim()),
      })
      setResults(result)
      setActiveTab('overview')
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Analysis failed. Ensure your site has been audited first and competitor URLs are valid.'
      )
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'gaps', label: `Content Gaps (${results?.gaps?.length || 0})` },
    { id: 'recommendations', label: `Recommendations (${results?.recommendations?.length || 0})` },
    { id: 'details', label: 'Details' },
  ]

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-navy mb-2">Competitive Gap Analysis</h1>
        <p className="text-gray-600">
          Compare your content against competitors to discover gaps, missed topics,
          and get actionable recommendations to outrank them.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 mb-8 shadow-sm">
        {/* Query */}
        <div className="mb-5">
          <label htmlFor="analysis-query" className="block text-sm font-medium text-gray-700 mb-1.5">
            Topic / Keyword to Analyze
          </label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              id="analysis-query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., RTO registration process, best laptops 2025"
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-navy/20 focus:border-navy"
              disabled={loading}
            />
          </div>
        </div>

        {/* My URL */}
        <div className="mb-5">
          <label htmlFor="my-url" className="block text-sm font-medium text-gray-700 mb-1.5">
            Your Site URL <span className="text-gray-400 font-normal">(must be previously audited)</span>
          </label>
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              id="my-url"
              type="text"
              value={myUrl}
              onChange={(e) => setMyUrl(e.target.value)}
              placeholder="https://yoursite.com/page"
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-navy/20 focus:border-navy"
              disabled={loading}
            />
          </div>
        </div>

        {/* Competitor URLs */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Competitor URLs <span className="text-gray-400 font-normal">(up to 5)</span>
          </label>
          <div className="space-y-2">
            {competitorUrls.map((url, index) => (
              <div key={index} className="flex items-center space-x-2">
                <div className="relative flex-1">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => updateCompetitor(index, e.target.value)}
                    placeholder={`https://competitor${index + 1}.com/page`}
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-navy/20 focus:border-navy"
                    disabled={loading}
                    aria-label={`Competitor URL ${index + 1}`}
                  />
                </div>
                {competitorUrls.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeCompetitor(index)}
                    className="p-2 text-gray-400 hover:text-crimson transition-colors"
                    aria-label={`Remove competitor ${index + 1}`}
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
          {competitorUrls.length < 5 && (
            <button
              type="button"
              onClick={addCompetitor}
              className="mt-2 flex items-center text-sm text-navy hover:text-navy/80 transition-colors"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add competitor
            </button>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !query.trim() || !myUrl.trim() || !competitorUrls.some(u => u.trim())}
          className="w-full py-3 bg-navy text-white font-semibold rounded-lg hover:bg-navy/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Analyzing content gaps...</span>
            </>
          ) : (
            <>
              <BarChart3 className="h-5 w-5" />
              <span>Run Gap Analysis</span>
            </>
          )}
        </button>

        {error && <p className="mt-3 text-crimson text-sm">{error}</p>}

        {loading && (
          <p className="mt-3 text-center text-sm text-gray-500">
            Fetching competitor content, embedding, reranking, and generating recommendations... This may take 30-60 seconds.
          </p>
        )}
      </form>

      {/* Results */}
      {results && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-navy">{(results.summary.content_overlap * 100).toFixed(0)}%</p>
              <p className="text-xs text-gray-500 mt-1">Content Overlap</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-crimson">{results.summary.total_gaps_found}</p>
              <p className="text-xs text-gray-500 mt-1">Gaps Found</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-forest">{results.summary.my_relevance?.toFixed(3)}</p>
              <p className="text-xs text-gray-500 mt-1">Your Relevance</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4 text-center">
              <p className={`text-2xl font-bold ${results.summary.depth_gap > 0 ? 'text-crimson' : 'text-forest'}`}>
                {results.summary.depth_gap > 0 ? '+' : ''}{results.summary.depth_gap}
              </p>
              <p className="text-xs text-gray-500 mt-1">Word Gap</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <div className="flex space-x-6 overflow-x-auto">
              {tabs.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-navy text-navy'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Side-by-side comparison */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* My Site */}
                <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
                  <div className="flex items-center space-x-2 mb-4">
                    <Target className="h-5 w-5 text-blue-600" />
                    <h3 className="font-semibold text-blue-900">Your Site</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Chunks Found</span>
                      <span className="font-medium">{results.comparison.my_site.chunks_found}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total Words</span>
                      <span className="font-medium">{results.comparison.my_site.total_words.toLocaleString()}</span>
                    </div>
                    <ScoreBar
                      label="Avg Relevance"
                      value={results.comparison.my_site.avg_similarity}
                      color="bg-blue-500"
                    />
                    {results.comparison.my_site.top_content_preview && (
                      <div className="mt-3 p-3 bg-white/70 rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Top content preview:</p>
                        <p className="text-sm text-gray-700 line-clamp-3">
                          {results.comparison.my_site.top_content_preview}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Competitor */}
                <div className="bg-orange-50 rounded-xl border border-orange-200 p-5">
                  <div className="flex items-center space-x-2 mb-4">
                    <Layers className="h-5 w-5 text-orange-600" />
                    <h3 className="font-semibold text-orange-900">Competitors</h3>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Chunks Found</span>
                      <span className="font-medium">{results.comparison.competitor.chunks_found}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Total Words</span>
                      <span className="font-medium">{results.comparison.competitor.total_words.toLocaleString()}</span>
                    </div>
                    <ScoreBar
                      label="Avg Relevance"
                      value={results.comparison.competitor.avg_similarity}
                      color="bg-orange-500"
                    />
                    {results.comparison.competitor.top_content_preview && (
                      <div className="mt-3 p-3 bg-white/70 rounded-lg">
                        <p className="text-xs text-gray-500 mb-1">Top content preview:</p>
                        <p className="text-sm text-gray-700 line-clamp-3">
                          {results.comparison.competitor.top_content_preview}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Overlap indicator */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <TrendingUp className="h-5 w-5 mr-2 text-navy" />
                  Content Overlap
                </h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Semantic similarity between your content and competitors</span>
                    <span className="font-bold text-gray-900">{(results.comparison.content_overlap * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-crimson via-amber to-forest"
                      style={{ width: `${results.comparison.content_overlap * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-400">
                    {results.comparison.content_overlap < 0.3
                      ? 'Low overlap — significant content differences exist.'
                      : results.comparison.content_overlap < 0.6
                      ? 'Moderate overlap — some shared topics but notable differences.'
                      : 'High overlap — content is fairly similar.'}
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'gaps' && (
            <div className="space-y-3">
              {results.gaps.length > 0 ? (
                <>
                  <div className="flex items-center space-x-2 mb-2">
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                    <p className="text-sm text-gray-600">
                      These are topics your competitors cover that are missing or underrepresented on your site.
                    </p>
                  </div>
                  {results.gaps.map((gap, i) => (
                    <GapCard key={i} gap={gap} index={i} />
                  ))}
                </>
              ) : (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <Target className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No significant content gaps detected. Your content covers the same ground as competitors.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'recommendations' && (
            <div className="space-y-3">
              {results.recommendations.length > 0 ? (
                <>
                  <div className="flex items-center space-x-2 mb-2">
                    <Lightbulb className="h-5 w-5 text-amber-500" />
                    <p className="text-sm text-gray-600">
                      Actionable steps to close the content gap and improve your ranking potential.
                    </p>
                  </div>
                  {results.recommendations.map((rec, i) => (
                    <RecommendationCard key={i} rec={rec} />
                  ))}
                </>
              ) : (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <Lightbulb className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No recommendations available.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'details' && (
            <div className="space-y-6">
              {/* Competitor breakdown */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
                  <Layers className="h-5 w-5 mr-2 text-orange-500" />
                  Competitor Breakdown
                </h3>
                <div className="space-y-3">
                  {Object.entries(results.competitor_details).map(([url, details]) => (
                    <div key={url} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900 truncate">{url}</p>
                      </div>
                      <div className="flex items-center space-x-4 ml-4 text-sm">
                        <span className="text-gray-500">{details.chunks_found} chunks</span>
                        <span className="font-medium text-gray-900">
                          {details.avg_similarity?.toFixed(3)} relevance
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top reranked results */}
              {results.reranked_results.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
                    <FileText className="h-5 w-5 mr-2 text-navy" />
                    Top Reranked Content
                  </h3>
                  <div className="space-y-3">
                    {results.reranked_results.map((result, i) => (
                      <div key={i} className="p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                            result.source === 'my_site'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-orange-100 text-orange-700'
                          }`}>
                            {result.source === 'my_site' ? 'Your Site' : 'Competitor'}
                          </span>
                          {result.rerank_score !== undefined && (
                            <span className="text-xs text-gray-400">
                              Score: {result.rerank_score?.toFixed(3)}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-2">{result.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

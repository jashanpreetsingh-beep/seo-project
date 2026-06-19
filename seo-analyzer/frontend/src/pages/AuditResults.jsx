/**
 * Audit Results Page - Shows the complete SEO audit report.
 * Displays health score, category breakdowns, and prioritized issues.
 */

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Globe, FileText, Code, Gauge, Lock, Shield, Brain,
  ArrowLeft, ExternalLink, Loader2
} from 'lucide-react'
import { getAudit } from '../api'
import ScoreCircle from '../components/ScoreCircle'
import CategoryCard from '../components/CategoryCard'
import IssueCard from '../components/IssueCard'
import GeoResults from './GeoResults'

export default function AuditResults() {
  const { id } = useParams()
  const [audit, setAudit] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    async function loadAudit() {
      try {
        const data = await getAudit(id)
        setAudit(data)
      } catch (err) {
        setError('Failed to load audit results.')
      } finally {
        setLoading(false)
      }
    }
    loadAudit()
  }, [id])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-navy" />
      </div>
    )
  }

  if (error || !audit) {
    return (
      <div className="text-center py-12">
        <p className="text-crimson">{error || 'Audit not found'}</p>
        <Link to="/" className="text-navy underline mt-4 inline-block">Back to analyzer</Link>
      </div>
    )
  }

  const categories = [
    { key: 'technical', title: 'Technical SEO', icon: Globe, score: audit.technical?.score || 0 },
    { key: 'content', title: 'Content Quality', icon: FileText, score: audit.content?.score || 0 },
    { key: 'onpage', title: 'On-Page SEO', icon: Shield, score: audit.onpage?.score || 0 },
    { key: 'schema', title: 'Schema Markup', icon: Code, score: audit.schema_markup?.score || 0 },
    { key: 'performance', title: 'Performance', icon: Gauge, score: audit.performance?.score || 0 },
    { key: 'security', title: 'Security', icon: Lock, score: audit.security?.score || 0 },
    { key: 'geo', title: 'GEO (AI Visibility)', icon: Brain, score: audit.geo?.geo_score || audit.geo_score || 0 },
  ]

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'geo', label: `GEO Score (${Math.round(audit.geo?.geo_score || audit.geo_score || 0)})` },
    { id: 'issues', label: `Issues (${audit.issues?.length || 0})` },
    { id: 'recommendations', label: 'Action Plan' },
  ]

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <Link to="/" className="text-gray-400 hover:text-navy transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-navy">Audit Results</h1>
            <a
              href={audit.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-gray-500 hover:text-navy flex items-center space-x-1"
            >
              <span>{audit.url}</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
        <div className="text-sm text-gray-500">
          {new Date(audit.created_at).toLocaleString()}
        </div>
      </div>

      {/* Score + Categories Row */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-8">
        {/* Score circles - SEO and GEO */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex items-center justify-center space-x-6">
          <ScoreCircle score={audit.health_score} size={120} label="SEO Score" />
          <ScoreCircle score={audit.geo?.geo_score || audit.geo_score || 0} size={120} label="GEO Score" />
        </div>

        {/* Category cards */}
        <div className="lg:col-span-3 grid grid-cols-2 md:grid-cols-3 gap-3">
          {categories.map(cat => (
            <CategoryCard
              key={cat.key}
              title={cat.title}
              score={cat.score}
              icon={cat.icon}
            />
          ))}
        </div>
      </div>

      {/* Issue Summary Bar */}
      <div className="flex items-center space-x-4 mb-6 bg-white rounded-lg border border-gray-200 p-4">
        <span className="text-sm font-medium text-gray-600">Issues:</span>
        {audit.critical_count > 0 && (
          <span className="px-2 py-1 text-xs font-bold rounded bg-red-100 text-red-800">
            {audit.critical_count} Critical
          </span>
        )}
        {audit.high_count > 0 && (
          <span className="px-2 py-1 text-xs font-bold rounded bg-orange-100 text-orange-800">
            {audit.high_count} High
          </span>
        )}
        {audit.medium_count > 0 && (
          <span className="px-2 py-1 text-xs font-bold rounded bg-yellow-100 text-yellow-800">
            {audit.medium_count} Medium
          </span>
        )}
        {audit.low_count > 0 && (
          <span className="px-2 py-1 text-xs font-bold rounded bg-blue-100 text-blue-800">
            {audit.low_count} Low
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400">
          Site type: <span className="font-medium capitalize">{audit.site_type}</span>
        </span>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex space-x-6">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
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
          {/* Technical details */}
          {audit.technical?.robots_txt && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Technical Details</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">robots.txt</span>
                  <p className="font-medium">{audit.technical.robots_txt.exists ? '✓ Found' : '✗ Missing'}</p>
                </div>
                <div>
                  <span className="text-gray-500">Sitemap</span>
                  <p className="font-medium">{audit.technical.sitemap?.found ? '✓ Found' : '✗ Missing'}</p>
                </div>
                <div>
                  <span className="text-gray-500">Canonical</span>
                  <p className="font-medium">{audit.technical.canonicals?.has_canonical ? '✓ Present' : '✗ Missing'}</p>
                </div>
                <div>
                  <span className="text-gray-500">HTTPS</span>
                  <p className="font-medium">{audit.technical.https?.is_https ? '✓ Secure' : '✗ Not secure'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Content stats */}
          {audit.content && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Content Analysis</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Word Count</span>
                  <p className="font-medium">{audit.content.word_count || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500">Readability</span>
                  <p className="font-medium">{audit.content.readability?.grade_level || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-gray-500">H1 Tags</span>
                  <p className="font-medium">{audit.content.headings?.h1_count || 0}</p>
                </div>
                <div>
                  <span className="text-gray-500">Thin Content</span>
                  <p className="font-medium">{audit.content.thin_content ? '⚠ Yes' : '✓ No'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Performance metrics */}
          {audit.performance && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Core Web Vitals</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                {['lcp', 'inp', 'cls', 'fcp', 'ttfb'].map(metric => {
                  const data = audit.performance[metric]
                  if (!data || !data.value) return null
                  return (
                    <div key={metric}>
                      <span className="text-gray-500 uppercase">{metric}</span>
                      <p className={`font-medium ${
                        data.rating === 'good' ? 'text-forest' :
                        data.rating === 'needs_improvement' ? 'text-amber' : 'text-crimson'
                      }`}>
                        {data.display || data.value}
                      </p>
                    </div>
                  )
                })}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                Source: {audit.performance.source === 'pagespeed_insights' ? 'Google PageSpeed Insights API' : 'HTML heuristic estimate'}
              </p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'geo' && (
        <GeoResults audit={audit} />
      )}

      {activeTab === 'issues' && (
        <div className="space-y-3">
          {audit.issues?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No issues found — great job!</p>
          ) : (
            audit.issues?.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))
          )}
        </div>
      )}

      {activeTab === 'recommendations' && (
        <div className="space-y-3">
          {audit.recommendations?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">No action items — everything looks good.</p>
          ) : (
            audit.recommendations?.map((rec, i) => (
              <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 flex items-start space-x-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-navy text-white flex items-center justify-center text-sm font-bold">
                  {rec.priority}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{rec.action}</p>
                  {rec.impact && <p className="text-sm text-gray-500 mt-1">{rec.impact}</p>}
                  <div className="flex items-center space-x-2 mt-2">
                    <span className={`px-2 py-0.5 text-xs rounded ${
                      rec.severity === 'critical' ? 'bg-red-100 text-red-700' :
                      rec.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {rec.severity}
                    </span>
                    <span className="text-xs text-gray-400">{rec.category}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

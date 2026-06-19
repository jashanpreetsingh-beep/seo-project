/**
 * Dashboard Page - Main entry point where users submit URLs for analysis.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Loader2, Globe, Shield, FileText, Code, Gauge, Lock } from 'lucide-react'
import { runAudit } from '../api'

export default function Dashboard() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError('')

    try {
      const result = await runAudit(url.trim())
      navigate(`/audit/${result.id}`)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Audit failed. Please check the URL and try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  const features = [
    { icon: Globe, title: 'Technical SEO', desc: 'Robots.txt, sitemaps, canonicals, redirects' },
    { icon: FileText, title: 'Content Quality', desc: 'E-E-A-T signals, readability, word count' },
    { icon: Code, title: 'Schema Markup', desc: 'JSON-LD detection, validation, suggestions' },
    { icon: Gauge, title: 'Core Web Vitals', desc: 'LCP, INP, CLS via PageSpeed Insights' },
    { icon: Search, title: 'On-Page SEO', desc: 'Title, meta description, headings, links' },
    { icon: Lock, title: 'Security', desc: 'HTTPS, security headers, mixed content' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold text-navy mb-3">
          SEO Analyzer
        </h1>
        <p className="text-lg text-gray-600">
          Comprehensive SEO analysis powered by LangGraph. Enter a URL to get a full audit
          with actionable recommendations.
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="mb-12">
        <div className="flex shadow-lg rounded-xl overflow-hidden border border-gray-200">
          <div className="flex-1 relative">
            <Globe className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter URL to analyze (e.g., example.com)"
              className="w-full pl-12 pr-4 py-4 text-lg border-none outline-none bg-white"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-8 py-4 bg-navy text-white font-semibold hover:bg-navy/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <Search className="h-5 w-5" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <p className="mt-3 text-crimson text-sm">{error}</p>
        )}

        {loading && (
          <div className="mt-4 text-center text-gray-500">
            <p className="text-sm">Running 6 analyzers in parallel... This takes 10-30 seconds.</p>
          </div>
        )}
      </form>

      {/* Feature Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="p-5 bg-white rounded-xl border border-gray-200 hover:border-navy/30 hover:shadow-sm transition-all"
          >
            <Icon className="h-8 w-8 text-navy mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
            <p className="text-sm text-gray-500">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

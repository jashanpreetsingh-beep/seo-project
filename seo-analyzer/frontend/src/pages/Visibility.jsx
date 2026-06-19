/**
 * AI Visibility Checker Page.
 * 
 * Ask an LLM what websites it recommends for a query,
 * then check if your URL appears in the results.
 */

import { useState } from 'react'
import { Search, Loader2, Eye, Cpu, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { checkVisibility } from '../api'

export default function Visibility() {
  const [query, setQuery] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [provider, setProvider] = useState('groq')
  const [numResults, setNumResults] = useState(20)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || !targetUrl.trim()) return

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const data = await checkVisibility({
        query: query.trim(),
        target_url: targetUrl.trim(),
        provider,
        num_results: numResults,
      })
      setResult(data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Visibility check failed. Please try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-navy mb-2">
          <Eye className="inline-block h-8 w-8 mr-2 -mt-1" />
          AI Visibility Checker
        </h1>
        <p className="text-gray-600">
          Check if LLMs recommend your website for a given search query.
          See where you rank in AI-generated results.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          {/* Query */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Search Query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder='e.g., "best project management tools"'
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none"
              disabled={loading}
            />
          </div>

          {/* Target URL */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Your URL to Check</label>
            <input
              type="text"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="e.g., yoursite.com"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none"
              disabled={loading}
            />
          </div>

          {/* Provider + Num Results */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none bg-white"
                disabled={loading}
              >
                <option value="groq">⚡ Groq (Free)</option>
                <option value="anthropic">🧠 Claude (Paid)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Results</label>
              <select
                value={numResults}
                onChange={(e) => setNumResults(Number(e.target.value))}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-navy/20 focus:border-navy outline-none bg-white"
                disabled={loading}
              >
                <option value={10}>Top 10</option>
                <option value={20}>Top 20</option>
                <option value={30}>Top 30</option>
              </select>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !query.trim() || !targetUrl.trim()}
          className="w-full py-3 bg-navy text-white font-semibold rounded-lg hover:bg-navy/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Checking AI visibility...</span>
            </>
          ) : (
            <>
              <Search className="h-5 w-5" />
              <span>Check Visibility</span>
            </>
          )}
        </button>

        {error && <p className="mt-3 text-crimson text-sm">{error}</p>}

        {loading && (
          <p className="mt-3 text-center text-sm text-gray-500">
            Querying LLM and validating URLs... This takes 15-30 seconds.
          </p>
        )}
      </form>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Result Banner */}
          <div className={`rounded-xl border-2 p-6 ${
            result.target_found
              ? 'bg-green-50 border-green-300'
              : 'bg-red-50 border-red-300'
          }`}>
            <div className="flex items-center space-x-4">
              {result.target_found ? (
                <CheckCircle className="h-10 w-10 text-green-600 flex-shrink-0" />
              ) : (
                <XCircle className="h-10 w-10 text-red-500 flex-shrink-0" />
              )}
              <div>
                {result.target_found ? (
                  <>
                    <h2 className="text-xl font-bold text-green-800">
                      Found at Rank #{result.target_rank}
                    </h2>
                    <p className="text-green-700">
                      Your site appears via{' '}
                      <span className="font-semibold">{result.match_type} match</span>
                      {' '}in {result.model}'s recommendations for "{result.query}"
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="text-xl font-bold text-red-800">Not Found</h2>
                    <p className="text-red-700">
                      Your site does not appear in {result.model}'s top {result.total_valid_results} recommendations for "{result.query}"
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-navy">{result.target_rank || '—'}</p>
              <p className="text-sm text-gray-500">Your Rank</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-navy">{result.total_valid_results}</p>
              <p className="text-sm text-gray-500">Valid Results</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-navy">{result.competitors_above?.length || 0}</p>
              <p className="text-sm text-gray-500">Competitors Above</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
              <p className="text-2xl font-bold text-navy capitalize">{result.match_type}</p>
              <p className="text-sm text-gray-500">Match Type</p>
            </div>
          </div>

          {/* Token Usage */}
          {result.token_usage && (
            <div className="flex items-center space-x-4 bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-200 p-4">
              <Cpu className="h-5 w-5 text-purple-600 flex-shrink-0" />
              <div className="flex items-center space-x-6 text-sm">
                <span className="font-medium text-purple-800">
                  {result.token_usage.provider === 'groq' ? '⚡ Groq' : '🧠 Claude'} Token Usage
                </span>
                <span className="text-purple-700">
                  <span className="text-gray-500">Input:</span>{' '}
                  <span className="font-semibold">{result.token_usage.input_tokens?.toLocaleString()}</span>
                </span>
                <span className="text-purple-700">
                  <span className="text-gray-500">Output:</span>{' '}
                  <span className="font-semibold">{result.token_usage.output_tokens?.toLocaleString()}</span>
                </span>
                <span className="text-purple-700">
                  <span className="text-gray-500">Total:</span>{' '}
                  <span className="font-bold">{result.token_usage.total_tokens?.toLocaleString()}</span>
                </span>
              </div>
              <span className="ml-auto text-xs text-purple-500 font-mono">{result.token_usage.model}</span>
            </div>
          )}

          {/* Results Table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">
                LLM Rankings for "{result.query}"
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Rank</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">URL</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Reason</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-600">Valid</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {result.results?.map((item, i) => {
                    const isTarget = item.url?.toLowerCase().includes(
                      result.target_url?.replace(/https?:\/\//, '').replace(/\/$/, '').toLowerCase()
                    )
                    return (
                      <tr
                        key={i}
                        className={isTarget ? 'bg-green-50 font-medium' : 'hover:bg-gray-50'}
                      >
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                            isTarget
                              ? 'bg-green-600 text-white'
                              : 'bg-gray-200 text-gray-700'
                          }`}>
                            {item.rank}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`hover:underline ${isTarget ? 'text-green-700' : 'text-navy'}`}
                          >
                            {item.url?.length > 50 ? item.url.substring(0, 50) + '...' : item.url}
                          </a>
                          {isTarget && (
                            <span className="ml-2 px-2 py-0.5 text-xs bg-green-600 text-white rounded-full">
                              YOUR SITE
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-600 max-w-xs truncate">
                          {item.reason}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {item.valid ? (
                            <CheckCircle className="h-4 w-4 text-green-500 inline" />
                          ) : (
                            <AlertTriangle className="h-4 w-4 text-amber-500 inline" />
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Competitors Above */}
          {result.competitors_above?.length > 0 && !result.target_found && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">Top Competitors (All ranked above you)</h3>
              <div className="flex flex-wrap gap-2">
                {result.competitors_above.slice(0, 15).map((domain, i) => (
                  <span
                    key={i}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                  >
                    #{i + 1} {domain}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

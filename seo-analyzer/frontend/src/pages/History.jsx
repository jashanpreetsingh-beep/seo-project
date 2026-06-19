/**
 * History Page - Shows all past audits with scores and links to results.
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Clock, ExternalLink, Loader2 } from 'lucide-react'
import { getHistory } from '../api'

export default function History() {
  const [audits, setAudits] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await getHistory()
        setAudits(data)
      } catch (err) {
        console.error('Failed to load history:', err)
      } finally {
        setLoading(false)
      }
    }
    loadHistory()
  }, [])

  const getScoreBadge = (score) => {
    if (score >= 80) return 'bg-green-100 text-green-800'
    if (score >= 50) return 'bg-orange-100 text-orange-800'
    return 'bg-red-100 text-red-800'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-navy" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-navy">Audit History</h1>
        <span className="text-sm text-gray-500">{audits.length} audits</span>
      </div>

      {audits.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Clock className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No audits yet. Run your first analysis!</p>
          <Link to="/" className="text-navy underline text-sm mt-2 inline-block">
            Go to Analyzer
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">URL</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">SEO</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">GEO</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="text-center px-4 py-3 text-xs font-medium text-gray-500 uppercase">Issues</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {audits.map((audit) => (
                <tr key={audit.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link
                      to={`/audit/${audit.id}`}
                      className="text-sm text-navy hover:underline flex items-center space-x-1"
                    >
                      <span className="truncate max-w-xs">{audit.url}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0" />
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 text-xs font-bold rounded ${getScoreBadge(audit.health_score)}`}>
                      {Math.round(audit.health_score)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 text-xs font-bold rounded ${getScoreBadge(audit.geo_score || 0)}`}>
                      {Math.round(audit.geo_score || 0)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs text-gray-500 capitalize">{audit.site_type || 'other'}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center space-x-1">
                      {audit.critical_count > 0 && (
                        <span className="text-xs text-red-600 font-medium">{audit.critical_count}C</span>
                      )}
                      {audit.high_count > 0 && (
                        <span className="text-xs text-orange-600 font-medium">{audit.high_count}H</span>
                      )}
                      {audit.medium_count > 0 && (
                        <span className="text-xs text-yellow-600 font-medium">{audit.medium_count}M</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-xs text-gray-500">
                    {new Date(audit.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

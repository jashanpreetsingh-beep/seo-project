/**
 * Displays a single SEO issue with severity indicator.
 */

import { AlertTriangle, AlertCircle, Info, XCircle } from 'lucide-react'

const severityConfig = {
  critical: {
    icon: XCircle,
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-800',
    label: 'Critical',
  },
  high: {
    icon: AlertTriangle,
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    badge: 'bg-orange-100 text-orange-800',
    label: 'High',
  },
  medium: {
    icon: AlertCircle,
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-800',
    label: 'Medium',
  },
  low: {
    icon: Info,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-800',
    label: 'Low',
  },
}

export default function IssueCard({ issue }) {
  const config = severityConfig[issue.severity] || severityConfig.medium
  const Icon = config.icon

  return (
    <div className={`p-4 rounded-lg border ${config.bg} ${config.border}`}>
      <div className="flex items-start space-x-3">
        <Icon className="h-5 w-5 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.badge}`}>
              {config.label}
            </span>
            <span className="text-xs text-gray-500 uppercase">{issue.category}</span>
          </div>
          <h4 className="font-semibold text-gray-900">{issue.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{issue.description}</p>
          {issue.recommendation && (
            <p className="text-sm text-gray-700 mt-2 font-medium">
              → {issue.recommendation}
            </p>
          )}
          {issue.impact && (
            <p className="text-xs text-gray-500 mt-1 italic">{issue.impact}</p>
          )}
        </div>
      </div>
    </div>
  )
}

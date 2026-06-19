/**
 * GEO Results Page - Shows Generative Engine Optimization analysis.
 * Displays GEO score, AI visibility level, category breakdowns,
 * priority actions, and 90-day improvement plan.
 */

import { useState } from 'react'
import {
  Brain, Eye, MessageSquare, Quote, Users, Target,
  TrendingUp, Calendar, ChevronDown, ChevronUp, Zap, Award
} from 'lucide-react'
import ScoreCircle from '../components/ScoreCircle'

const categoryIcons = {
  entity_understanding: Target,
  answer_extraction: MessageSquare,
  authority_trust: Award,
  citation_probability: Quote,
  conversational_search: Users,
}

const categoryColors = {
  entity_understanding: 'from-purple-500 to-purple-600',
  answer_extraction: 'from-blue-500 to-blue-600',
  authority_trust: 'from-green-500 to-green-600',
  citation_probability: 'from-orange-500 to-orange-600',
  conversational_search: 'from-pink-500 to-pink-600',
}

function GeoScoreBar({ label, score, weight, icon: Icon }) {
  const getColor = (s) => {
    if (s >= 70) return 'bg-forest'
    if (s >= 40) return 'bg-amber'
    return 'bg-crimson'
  }

  return (
    <div className="flex items-center space-x-3 py-2">
      <Icon className="h-5 w-5 text-gray-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-gray-700 truncate">{label}</span>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400">{weight}</span>
            <span className={`text-sm font-bold ${score >= 70 ? 'text-forest' : score >= 40 ? 'text-amber' : 'text-crimson'}`}>
              {Math.round(score)}
            </span>
          </div>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${getColor(score)}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function VisibilityBadge({ visibility }) {
  const levelColors = {
    'Excellent': 'bg-green-100 text-green-800 border-green-300',
    'Strong': 'bg-blue-100 text-blue-800 border-blue-300',
    'Moderate': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'Weak': 'bg-orange-100 text-orange-800 border-orange-300',
    'Poor': 'bg-red-100 text-red-800 border-red-300',
  }

  const colorClass = levelColors[visibility?.level] || levelColors['Poor']

  return (
    <div className={`inline-flex items-center px-3 py-1.5 rounded-full border text-sm font-medium ${colorClass}`}>
      <Eye className="h-4 w-4 mr-1.5" />
      AI Visibility: {visibility?.level || 'Unknown'}
    </div>
  )
}

function PriorityActionCard({ action }) {
  const [expanded, setExpanded] = useState(false)

  const impactColors = {
    'Very High': 'bg-red-100 text-red-700',
    'High': 'bg-orange-100 text-orange-700',
    'Medium': 'bg-yellow-100 text-yellow-700',
    'Low': 'bg-blue-100 text-blue-700',
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 text-white flex items-center justify-center text-sm font-bold">
          {action.priority}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900">{action.issue}</p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${impactColors[action.impact] || 'bg-gray-100 text-gray-700'}`}>
              {action.impact} Impact
            </span>
            <span className="px-2 py-0.5 text-xs rounded bg-purple-100 text-purple-700 font-medium">
              {action.estimated_score_gain}
            </span>
            {action.effort && (
              <span className="text-xs text-gray-400">{action.effort}</span>
            )}
          </div>

          {action.solution && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center text-xs text-navy mt-2 hover:underline"
            >
              {expanded ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
              {expanded ? 'Hide solution' : 'Show solution'}
            </button>
          )}

          {expanded && action.solution && (
            <div className="mt-2 p-3 bg-gray-50 rounded-md text-sm text-gray-700">
              {action.solution}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MonthPlan({ month, data }) {
  const monthLabels = { month_1: 'Month 1', month_2: 'Month 2', month_3: 'Month 3' }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="font-semibold text-gray-900">{monthLabels[month]}</h4>
          <p className="text-sm text-gray-500">{data.title}</p>
        </div>
        <span className="px-2 py-1 text-xs font-bold rounded bg-green-100 text-green-700">
          +{data.expected_gain} GEO
        </span>
      </div>
      <p className="text-xs text-gray-400 mb-3">{data.focus}</p>
      <ul className="space-y-2">
        {data.tasks?.map((task, i) => (
          <li key={i} className="flex items-start space-x-2 text-sm text-gray-700">
            <span className="text-purple-500 mt-0.5">•</span>
            <span>{task}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function GeoResults({ audit }) {
  const [activeGeoTab, setActiveGeoTab] = useState('overview')

  const geo = audit?.geo || {}
  const geoScore = geo.geo_score || audit?.geo_score || 0

  if (!geo || !geo.scores) {
    return (
      <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
        <Brain className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500">GEO analysis not available for this audit.</p>
      </div>
    )
  }

  const scores = geo.scores || {}
  const geoTabs = [
    { id: 'overview', label: 'GEO Overview' },
    { id: 'actions', label: `Actions (${geo.priority_actions?.length || 0})` },
    { id: 'plan', label: '90-Day Plan' },
  ]

  return (
    <div className="space-y-6">
      {/* GEO Header */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <Brain className="h-7 w-7 text-purple-600" />
          <div>
            <h2 className="text-xl font-bold text-gray-900">GEO Analysis</h2>
            <p className="text-sm text-gray-600">Generative Engine Optimization — AI Search Visibility</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          {/* GEO Score Circle */}
          <div className="flex justify-center">
            <ScoreCircle score={geoScore} size={130} label="GEO Score" />
          </div>

          {/* Visibility + Potential */}
          <div className="space-y-3">
            <VisibilityBadge visibility={geo.visibility} />
            <p className="text-sm text-gray-600">{geo.visibility?.description}</p>
            {geo.potential_score > 0 && (
              <div className="flex items-center space-x-2 text-sm">
                <TrendingUp className="h-4 w-4 text-green-600" />
                <span className="text-gray-600">
                  Potential: <span className="font-bold text-green-700">{Math.round(geo.potential_score)}</span>
                  <span className="text-gray-400 ml-1">(+{Math.round(geo.total_potential_gain)} achievable)</span>
                </span>
              </div>
            )}
          </div>

          {/* Strengths/Weaknesses summary */}
          <div className="space-y-2">
            {geo.strengths?.slice(0, 2).map((s, i) => (
              <div key={i} className="flex items-center text-sm text-green-700">
                <span className="mr-2">✓</span> {s.category} ({Math.round(s.score)})
              </div>
            ))}
            {geo.weaknesses?.slice(0, 2).map((w, i) => (
              <div key={i} className="flex items-center text-sm text-red-600">
                <span className="mr-2">✗</span> {w.category} ({Math.round(w.score)})
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* GEO Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex space-x-6">
          {geoTabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveGeoTab(tab.id)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeGeoTab === tab.id
                  ? 'border-purple-600 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeGeoTab === 'overview' && (
        <div className="space-y-6">
          {/* Category Score Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
              <Zap className="h-5 w-5 mr-2 text-purple-500" />
              GEO Score Breakdown
            </h3>
            <div className="space-y-1">
              {Object.entries(scores).map(([key, data]) => {
                const Icon = categoryIcons[key] || Brain
                return (
                  <GeoScoreBar
                    key={key}
                    label={data.label || key}
                    score={data.score || 0}
                    weight={data.weight || ''}
                    icon={Icon}
                  />
                )
              })}
            </div>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-green-50 rounded-xl border border-green-200 p-5">
              <h4 className="font-semibold text-green-800 mb-3">✓ Strengths</h4>
              {geo.strengths?.length > 0 ? (
                <ul className="space-y-2">
                  {geo.strengths.map((s, i) => (
                    <li key={i} className="flex items-center justify-between text-sm">
                      <span className="text-green-700">{s.category}</span>
                      <span className="font-bold text-green-800">{Math.round(s.score)}/100</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-green-600">Keep building — strengths will appear as scores improve.</p>
              )}
            </div>

            <div className="bg-red-50 rounded-xl border border-red-200 p-5">
              <h4 className="font-semibold text-red-800 mb-3">✗ Weaknesses</h4>
              {geo.weaknesses?.length > 0 ? (
                <ul className="space-y-2">
                  {geo.weaknesses.map((w, i) => (
                    <li key={i} className="flex items-center justify-between text-sm">
                      <span className="text-red-700">{w.category}</span>
                      <span className="font-bold text-red-800">{Math.round(w.score)}/100</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-red-600">No major weaknesses detected.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeGeoTab === 'actions' && (
        <div className="space-y-3">
          {geo.priority_actions?.length > 0 ? (
            geo.priority_actions.map((action, i) => (
              <PriorityActionCard key={i} action={action} />
            ))
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Zap className="h-8 w-8 mx-auto mb-2 text-gray-300" />
              <p>No priority actions generated.</p>
            </div>
          )}
        </div>
      )}

      {activeGeoTab === 'plan' && (
        <div className="space-y-4">
          <div className="flex items-center space-x-2 mb-2">
            <Calendar className="h-5 w-5 text-purple-500" />
            <h3 className="font-semibold text-gray-900">90-Day GEO Improvement Plan</h3>
          </div>

          {geo.plan_90_day ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MonthPlan month="month_1" data={geo.plan_90_day.month_1 || {}} />
              <MonthPlan month="month_2" data={geo.plan_90_day.month_2 || {}} />
              <MonthPlan month="month_3" data={geo.plan_90_day.month_3 || {}} />
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No 90-day plan available.</p>
          )}

          {/* Expected outcome */}
          {geo.potential_score > 0 && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-200 p-5 mt-4">
              <h4 className="font-semibold text-green-800 mb-2">Expected Outcome After 90 Days</h4>
              <div className="flex items-center space-x-6">
                <div>
                  <span className="text-sm text-gray-500">Current GEO Score</span>
                  <p className="text-2xl font-bold text-gray-700">{Math.round(geoScore)}</p>
                </div>
                <TrendingUp className="h-6 w-6 text-green-500" />
                <div>
                  <span className="text-sm text-gray-500">Projected GEO Score</span>
                  <p className="text-2xl font-bold text-green-700">{Math.round(geo.potential_score)}</p>
                </div>
                <div className="ml-auto text-right">
                  <span className="text-sm text-gray-500">Total Gain</span>
                  <p className="text-xl font-bold text-green-600">+{Math.round(geo.total_potential_gain)}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Category score card - shows score for one analysis category.
 */

export default function CategoryCard({ title, score, icon: Icon, details }) {
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-forest'
    if (score >= 50) return 'text-amber'
    return 'text-crimson'
  }

  const getBarColor = (score) => {
    if (score >= 80) return 'bg-forest'
    if (score >= 50) return 'bg-amber'
    return 'bg-crimson'
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {Icon && <Icon className="h-5 w-5 text-navy" />}
          <h3 className="font-semibold text-gray-900">{title}</h3>
        </div>
        <span className={`text-2xl font-bold ${getScoreColor(score)}`}>
          {Math.round(score)}
        </span>
      </div>

      {/* Score bar */}
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${getBarColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>

      {/* Optional details */}
      {details && (
        <p className="text-xs text-gray-500 mt-2">{details}</p>
      )}
    </div>
  )
}

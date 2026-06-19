/**
 * Animated circular score display.
 * Shows the health score (0-100) with color coding:
 * - Green (80-100): Good
 * - Amber (50-79): Needs improvement
 * - Red (0-49): Poor
 */

export default function ScoreCircle({ score, size = 120, label = "Health Score" }) {
  const radius = (size - 12) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const offset = circumference - progress

  const getColor = (score) => {
    if (score >= 80) return { stroke: '#2d6a4f', text: 'text-forest', bg: 'bg-green-50' }
    if (score >= 50) return { stroke: '#d4740e', text: 'text-amber', bg: 'bg-orange-50' }
    return { stroke: '#c53030', text: 'text-crimson', bg: 'bg-red-50' }
  }

  const colors = getColor(score)

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="transform -rotate-90" width={size} height={size}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#e5e7eb"
            strokeWidth="8"
            fill="none"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={colors.stroke}
            strokeWidth="8"
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        {/* Score text in center */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-3xl font-bold ${colors.text}`}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      <span className="mt-2 text-sm text-gray-600 font-medium">{label}</span>
    </div>
  )
}

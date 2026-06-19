import { Link, useLocation } from 'react-router-dom'
import { Search, History, BarChart3, Eye } from 'lucide-react'

export default function Layout({ children }) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Analyzer', icon: Search },
    { path: '/visibility', label: 'AI Visibility', icon: Eye },
    { path: '/history', label: 'History', icon: History },
  ]

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-navy text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center space-x-2">
              <BarChart3 className="h-8 w-8 text-gold" />
              <span className="text-xl font-bold">SEO Analyzer</span>
            </Link>
            <nav className="flex space-x-4">
              {navItems.map(({ path, label, icon: Icon }) => (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center space-x-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    location.pathname === path
                      ? 'bg-white/20 text-white'
                      : 'text-gray-300 hover:text-white hover:bg-white/10'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}

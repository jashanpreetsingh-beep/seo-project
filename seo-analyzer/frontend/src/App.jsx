import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import AuditResults from './pages/AuditResults'
import History from './pages/History'
import Visibility from './pages/Visibility'
import CompetitiveAnalysis from './pages/CompetitiveAnalysis'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/audit/:id" element={<AuditResults />} />
        <Route path="/history" element={<History />} />
        <Route path="/visibility" element={<Visibility />} />
        <Route path="/competitive" element={<CompetitiveAnalysis />} />
      </Routes>
    </Layout>
  )
}

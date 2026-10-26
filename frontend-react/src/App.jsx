import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import HomePage from './components/HomePage'
import AnalysisPage from './components/AnalysisPage'
import HistoryPage from './components/HistoryPage'
import StatsPage from './components/StatsPage'

function App() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats')
      const data = await response.json()
      if (data.success) {
        setStats(data.stats)
      }
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500">
        {/* Navigation */}
        <nav className="bg-white/10 backdrop-blur-md border-b border-white/20">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <Link to="/" className="text-white font-fugaz text-2xl hover:text-yellow-300 transition">
                LinkedIA
              </Link>
              <div className="flex gap-6">
                <Link to="/" className="text-white hover:text-yellow-300 transition font-medium">
                  Home
                </Link>
                <Link to="/analysis" className="text-white hover:text-yellow-300 transition font-medium">
                  Analisi
                </Link>
                <Link to="/history" className="text-white hover:text-yellow-300 transition font-medium">
                  Storico
                </Link>
                <Link to="/stats" className="text-white hover:text-yellow-300 transition font-medium">
                  Statistiche
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage stats={stats} />} />
            <Route path="/analysis" element={<AnalysisPage onAnalysisComplete={fetchStats} />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/stats" element={<StatsPage stats={stats} />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="mt-16 pb-8 text-center text-white/80">
          <p className="text-sm">
            © 2025 LinkedIA - Linked Intelligent Analyst | Università del Piemonte Orientale
          </p>
        </footer>
      </div>
    </Router>
  )
}

export default App

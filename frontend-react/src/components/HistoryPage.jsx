import React, { useState, useEffect } from 'react'
import { Clock, Search, FileText } from 'lucide-react'

function HistoryPage() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/history')
      const data = await response.json()
      if (data.success) {
        setHistory(data.history)
      }
    } catch (error) {
      console.error('Error fetching history:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredHistory = history.filter(item =>
    item.date.includes(searchTerm)
  )

  if (loading) {
    return (
      <div className="text-center text-white">
        <p className="text-xl">Caricamento storico...</p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="font-fugaz text-4xl text-white mb-8 text-center">
        Storico Analisi
      </h1>

      {/* Search Bar */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Cerca per data..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-12 pr-4 py-3 rounded-lg border-2 border-white/30 bg-white/90 focus:outline-none focus:border-yellow-400 transition"
          />
        </div>
      </div>

      {/* History List */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
        {filteredHistory.length === 0 ? (
          <div className="text-center text-white/70 py-12">
            <FileText className="mx-auto mb-4" size={48} />
            <p>Nessuna analisi trovata</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item, idx) => (
              <HistoryItem key={idx} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function HistoryItem({ item }) {
  const [details, setDetails] = useState(null)
  const [showDetails, setShowDetails] = useState(false)

  const loadDetails = async () => {
    if (!showDetails && !details) {
      try {
        const response = await fetch(`/api/article/${item.date}`)
        const data = await response.json()
        if (data.success) {
          setDetails(data.articles)
        }
      } catch (error) {
        console.error('Error loading details:', error)
      }
    }
    setShowDetails(!showDetails)
  }

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10 hover:bg-white/10 transition">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Clock className="text-yellow-300" size={20} />
          <div>
            <p className="text-white font-semibold">{item.date}</p>
            <p className="text-white/70 text-sm">
              {item.article_count} articoli | {item.analyzed_count} analizzati
            </p>
          </div>
        </div>
        <button
          onClick={loadDetails}
          className="text-yellow-300 hover:text-yellow-400 text-sm font-semibold"
        >
          {showDetails ? 'Nascondi' : 'Dettagli'}
        </button>
      </div>

      {showDetails && details && (
        <div className="mt-4 pt-4 border-t border-white/10 space-y-3">
          {details.map((article, idx) => (
            <div key={idx} className="text-white/90 text-sm">
              <p className="font-semibold mb-1">{article.title}</p>
              {article.report_nesso && (
                <p className="text-white/70 text-xs bg-black/30 p-2 rounded">
                  {article.report_nesso}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HistoryPage

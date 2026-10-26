import React, { useState } from 'react'
import { Calendar, Loader, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react'

function AnalysisPage({ onAnalysisComplete }) {
  const [date, setDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleAnalyze = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    console.log('=== FRONTEND: Invio richiesta al backend ===')
    console.log('Data selezionata:', date)
    console.log('URL chiamata: /api/analyze')

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ date }),
      })

      console.log('=== FRONTEND: Risposta ricevuta ===')
      console.log('Status:', response.status)
      
      const data = await response.json()
      console.log('Data:', data)

      if (response.ok) {
        setResult(data)
        if (onAnalysisComplete) onAnalysisComplete()
      } else {
        setError(data.error || 'Errore durante l\'analisi')
      }
    } catch (err) {
      console.error('=== FRONTEND: ERRORE ===', err)
      setError('Errore di connessione al server')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="font-fugaz text-4xl text-white mb-8 text-center">
        Analisi Geopolitico-Finanziaria
      </h1>

      {/* Analysis Form */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-8 border border-white/20 mb-8">
        <form onSubmit={handleAnalyze} className="max-w-md mx-auto">
          <label className="block text-white font-semibold mb-2">
            Seleziona Data (YYYY-MM-DD)
          </label>
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full pl-12 pr-4 py-3 rounded-lg border-2 border-white/30 bg-white/90 focus:outline-none focus:border-yellow-400 transition"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-bold px-8 py-3 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Analisi...' : 'Analizza'}
            </button>
          </div>
        </form>

        {/* Loading State */}
        {loading && (
          <div className="mt-8 text-center">
            <Loader className="inline-block animate-spin text-yellow-300 mb-4" size={48} />
            <p className="text-white">Analisi in corso... L'operazione potrebbe richiedere qualche minuto.</p>
            <div className="mt-4 space-y-2 text-white/70 text-sm">
              <p>→ Ricerca notizie...</p>
              <p>→ Download dati mercato...</p>
              <p>→ Calcolo indicatori...</p>
              <p>→ Analisi AI in corso...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="mt-8 bg-red-500/20 border border-red-500 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="text-red-300 flex-shrink-0" size={24} />
            <div className="text-white">
              <p className="font-semibold mb-1">Errore</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {result && result.success && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="bg-green-500/20 border border-green-400 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="text-green-300" size={32} />
              <h2 className="text-2xl font-bold text-white">Analisi Completata</h2>
            </div>
            <div className="grid md:grid-cols-3 gap-4 text-white">
              <div>
                <p className="text-white/70 text-sm">Data</p>
                <p className="font-semibold text-lg">{result.date}</p>
              </div>
              <div>
                <p className="text-white/70 text-sm">Articoli Trovati</p>
                <p className="font-semibold text-lg">{result.articles_found}</p>
              </div>
              <div>
                <p className="text-white/70 text-sm">Analisi Eseguite</p>
                <p className="font-semibold text-lg">{result.analysis?.length || 0}</p>
              </div>
            </div>
          </div>

          {/* Articles */}
          {result.articles && result.articles.length > 0 && (
            <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
              <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp size={24} />
                Articoli e Analisi
              </h3>
              <div className="space-y-4">
                {result.articles.map((article, idx) => (
                  <ArticleCard key={idx} article={article} analysis={result.analysis?.[idx]} />
                ))}
              </div>
            </div>
          )}

          {/* LiA Prediction */}
          {result.lia_prediction && (
            <div className="bg-yellow-400/20 border border-yellow-400 rounded-xl p-6">
              <h3 className="text-2xl font-bold text-white mb-4">LiA - Sentenza Finale</h3>
              <div className="text-white bg-black/30 p-4 rounded-lg">
                <pre className="whitespace-pre-wrap font-mono text-sm">
                  {JSON.stringify(result.lia_prediction, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Funzione helper per pulire il testo dalle citazioni [1], [2], [3]
function cleanCitations(text) {
  if (!text) return text
  return text.replace(/\[\d+\]/g, '').replace(/\s+/g, ' ').trim()
}

// Funzione helper per formattare i prezzi in modo ordinato
function formatPrices(prezzi) {
  if (!prezzi || Object.keys(prezzi).length === 0) return null
  
  const indices = ['SP500', 'NASDAQ', 'DAX', 'FTSE100', 'NIKKEI']
  const priceTypes = ['Open', 'High', 'Low', 'Close', 'Volume']
  
  const organized = {}
  indices.forEach(idx => {
    const indexData = {}
    priceTypes.forEach(type => {
      const key = `${idx}_${type}`
      if (prezzi[key] !== undefined && prezzi[key] !== null && !isNaN(prezzi[key])) {
        indexData[type] = typeof prezzi[key] === 'number' ? prezzi[key].toFixed(2) : prezzi[key]
      }
    })
    if (Object.keys(indexData).length > 0) {
      organized[idx] = indexData
    }
  })
  
  return Object.keys(organized).length > 0 ? organized : null
}

// Funzione helper per formattare gli addons in modo ordinato
function formatAddons(addons) {
  if (!addons || Object.keys(addons).length === 0) return null
  
  const indices = ['SP500', 'NASDAQ', 'DAX', 'FTSE100', 'NIKKEI']
  const addonTypes = ['gap_ret', 'intra_ret', 'range_pct', 'atr7', 'rv7', 'zscore7', 'momentum7']
  
  const organized = {}
  indices.forEach(idx => {
    const indexData = {}
    addonTypes.forEach(type => {
      const key = `${idx}_${type}`
      if (addons[key] !== undefined && addons[key] !== null && !isNaN(addons[key])) {
        const val = parseFloat(addons[key])
        indexData[type] = val.toFixed(4)
      }
    })
    if (Object.keys(indexData).length > 0) {
      organized[idx] = indexData
    }
  })
  
  return Object.keys(organized).length > 0 ? organized : null
}

function ArticleCard({ article, analysis }) {
  const [expanded, setExpanded] = useState(false)
  
  const cleanedCorpo = cleanCitations(article.Corpo)
  const formattedPrices = formatPrices(article.prezzi)
  const formattedAddons = formatAddons(article.addons)

  return (
    <div className="bg-white/5 rounded-lg p-4 border border-white/10">
      <h4 className="text-xl font-semibold text-white mb-2">{cleanCitations(article.Titolo)}</h4>
      
      {expanded && (
        <div className="mt-4 space-y-4">
          {cleanedCorpo && (
            <div>
              <p className="text-white/90 text-sm leading-relaxed">{cleanedCorpo}</p>
            </div>
          )}
          
          {formattedPrices && (
            <div>
              <p className="text-yellow-300 font-semibold text-sm mb-2">Prezzi di Mercato (OHLCV)</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(formattedPrices).map(([index, data]) => (
                  <div key={index} className="bg-black/40 p-3 rounded-lg border border-white/10">
                    <p className="text-yellow-400 font-bold text-sm mb-2">{index}</p>
                    <div className="grid grid-cols-2 gap-1 text-xs">
                      {data.Open && <p className="text-white/70">Open: <span className="text-white">{data.Open}</span></p>}
                      {data.High && <p className="text-white/70">High: <span className="text-green-400">{data.High}</span></p>}
                      {data.Low && <p className="text-white/70">Low: <span className="text-red-400">{data.Low}</span></p>}
                      {data.Close && <p className="text-white/70">Close: <span className="text-white font-semibold">{data.Close}</span></p>}
                      {data.Volume && <p className="text-white/70 col-span-2">Vol: <span className="text-blue-300">{parseInt(data.Volume).toLocaleString()}</span></p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {formattedAddons && (
            <div>
              <p className="text-yellow-300 font-semibold text-sm mb-2">Indicatori Tecnici</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(formattedAddons).map(([index, data]) => (
                  <div key={index} className="bg-black/40 p-3 rounded-lg border border-white/10">
                    <p className="text-yellow-400 font-bold text-sm mb-2">{index}</p>
                    <div className="grid grid-cols-2 gap-1 text-xs">
                      {data.gap_ret && <p className="text-white/70">Gap: <span className={parseFloat(data.gap_ret) >= 0 ? 'text-green-400' : 'text-red-400'}>{data.gap_ret}%</span></p>}
                      {data.intra_ret && <p className="text-white/70">Intra: <span className={parseFloat(data.intra_ret) >= 0 ? 'text-green-400' : 'text-red-400'}>{data.intra_ret}%</span></p>}
                      {data.atr7 && <p className="text-white/70">ATR7: <span className="text-blue-300">{data.atr7}</span></p>}
                      {data.rv7 && <p className="text-white/70">RV7: <span className="text-blue-300">{data.rv7}</span></p>}
                      {data.zscore7 && <p className="text-white/70">Z-Score: <span className="text-purple-300">{data.zscore7}</span></p>}
                      {data.momentum7 && <p className="text-white/70">Mom7: <span className={parseFloat(data.momentum7) >= 0 ? 'text-green-400' : 'text-red-400'}>{data.momentum7}</span></p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis && analysis.report_nesso && (
            <div>
              <p className="text-green-300 font-semibold text-sm mb-2">Report Nesso</p>
              <div className="bg-black/30 p-4 rounded-lg text-sm text-white/90 leading-relaxed border-l-4 border-green-400">
                {cleanCitations(analysis.report_nesso)}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-yellow-300 hover:text-yellow-400 text-sm font-semibold"
      >
        {expanded ? '▲ Nascondi dettagli' : '▼ Mostra dettagli'}
      </button>
    </div>
  )
}

export default AnalysisPage

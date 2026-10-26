import React from 'react'
import { BarChart, Database, TrendingUp, Calendar } from 'lucide-react'

function StatsPage({ stats }) {
  if (!stats) {
    return (
      <div className="text-center text-white">
        <p className="text-xl">Caricamento statistiche...</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="font-fugaz text-4xl text-white mb-8 text-center">
        Statistiche Sistema
      </h1>

      {/* Main Stats Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <StatCard
          icon={<Database size={32} />}
          label="Articoli Totali"
          value={stats.total_articles}
          color="bg-blue-500/20 border-blue-400"
        />
        <StatCard
          icon={<Calendar size={32} />}
          label="Date Analizzate"
          value={stats.total_dates}
          color="bg-green-500/20 border-green-400"
        />
        <StatCard
          icon={<TrendingUp size={32} />}
          label="Analisi Complete"
          value={stats.analyzed_articles}
          color="bg-purple-500/20 border-purple-400"
        />
      </div>

      {/* Date Range */}
      {stats.date_range && (
        <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 mb-8">
          <h2 className="text-2xl font-bold text-white mb-4">Intervallo Temporale</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="text-white">
              <p className="text-white/70 mb-1">Prima Analisi</p>
              <p className="text-2xl font-bold text-yellow-300">{stats.date_range.earliest || 'N/A'}</p>
            </div>
            <div className="text-white">
              <p className="text-white/70 mb-1">Ultima Analisi</p>
              <p className="text-2xl font-bold text-yellow-300">{stats.date_range.latest || 'N/A'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tracked Indices */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
        <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
          <BarChart size={24} />
          Indici Monitorati
        </h2>
        <div className="grid md:grid-cols-5 gap-4">
          {stats.indices_tracked?.map((index, idx) => (
            <div key={idx} className="bg-white/5 rounded-lg p-4 text-center border border-white/10">
              <p className="text-white font-bold text-lg">{index}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Add-ons Info */}
      <div className="mt-8 bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
        <h2 className="text-2xl font-bold text-white mb-4">Indicatori Calcolati</h2>
        <div className="grid md:grid-cols-2 gap-6 text-white">
          <div>
            <h3 className="font-semibold text-yellow-300 mb-2">Core Add-ons (7)</h3>
            <ul className="text-sm space-y-1 text-white/80">
              <li>• Gap Return</li>
              <li>• Intraday Return</li>
              <li>• Range %</li>
              <li>• True Range</li>
              <li>• ATR (7 giorni)</li>
              <li>• Realized Volatility (7 giorni)</li>
              <li>• Rogers-Satchell Volatility (7 giorni)</li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold text-yellow-300 mb-2">Extra Add-ons (7)</h3>
            <ul className="text-sm space-y-1 text-white/80">
              <li>• Rolling Min/Max (7 giorni)</li>
              <li>• Z-Score (7 giorni)</li>
              <li>• Percentile (7 giorni)</li>
              <li>• Drawdown</li>
              <li>• Momentum (7 giorni)</li>
              <li>• Volatility (7 giorni)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className={`${color} backdrop-blur-md rounded-xl p-6 border`}>
      <div className="flex items-center gap-4">
        <div className="text-white">{icon}</div>
        <div>
          <p className="text-white/70 text-sm">{label}</p>
          <p className="text-3xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  )
}

export default StatsPage
